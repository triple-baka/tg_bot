import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from config import OWNER_IDS, Tariff


DATABASE = "data/bot.db"


@contextmanager
def get_db():

    conn = sqlite3.connect(
        DATABASE,
        check_same_thread=False,
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()




def init_db():

    with get_db() as db:

        db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_subscribed BOOLEAN DEFAULT FALSE,
                subscribed_until TIMESTAMP DEFAULT NULL,
                tariff TEXT DEFAULT NULL,
                trial_used BOOLEAN DEFAULT FALSE,
                delete_on_expiration BOOLEAN DEFAULT TRUE,
                subscription_id TEXT DEFAULT NULL
            )
        """)

        db.commit()

    migrate_tags()


def migrate_tags():

    with get_db() as db:

        try:
            db.execute("BEGIN IMMEDIATE")

            db.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            """)

            columns = {
                row["name"]
                for row in db.execute(
                    "PRAGMA table_info(user_tags)"
                ).fetchall()
            }

            # Старая таблица отсутствует
            if not columns:

                db.execute("""
                    CREATE TABLE user_tags (
                        user_id INTEGER NOT NULL,
                        tag_id INTEGER NOT NULL,

                        UNIQUE(user_id, tag_id),

                        FOREIGN KEY(user_id)
                            REFERENCES users(user_id)
                            ON DELETE CASCADE,

                        FOREIGN KEY(tag_id)
                            REFERENCES tags(id)
                            ON DELETE CASCADE
                    )
                """)

            # Старая структура user_id + tag
            elif "tag" in columns:

                db.execute("""
                    ALTER TABLE user_tags
                    RENAME TO user_tags_legacy
                """)

                db.execute("""
                    INSERT OR IGNORE INTO tags (name)
                    SELECT DISTINCT tag
                    FROM user_tags_legacy
                    WHERE tag IS NOT NULL
                """)

                db.execute("""
                    CREATE TABLE user_tags (
                        user_id INTEGER NOT NULL,
                        tag_id INTEGER NOT NULL,

                        UNIQUE(user_id, tag_id),

                        FOREIGN KEY(user_id)
                            REFERENCES users(user_id)
                            ON DELETE CASCADE,

                        FOREIGN KEY(tag_id)
                            REFERENCES tags(id)
                            ON DELETE CASCADE
                    )
                """)

                db.execute("""
                    INSERT OR IGNORE INTO user_tags
                        (user_id, tag_id)
                    SELECT
                        old.user_id,
                        tags.id
                    FROM user_tags_legacy old
                    INNER JOIN tags
                        ON tags.name = old.tag
                """)

                db.execute("""
                    DROP TABLE user_tags_legacy
                """)

            # Проверяем новую структуру
            elif not {"user_id", "tag_id"}.issubset(columns):
                raise RuntimeError(
                    f"Неизвестная структура user_tags: {columns}"
                )

            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_tags_tag_id
                ON user_tags(tag_id)
            """)

            db.commit()

        except Exception:
            db.rollback()
            raise

def add_user(user):

    with get_db() as db:

        db.execute(
            """
            INSERT INTO users
            (
                user_id,
                username
            )
            VALUES (?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                username=excluded.username
            """,
            (
                user.id,
                user.username,
            ),
        )

        db.commit()



def get_all_users():

    with get_db() as db:

        placeholders = ",".join(
            "?" for _ in OWNER_IDS
        )

        rows = db.execute(
            f"""
            SELECT
                user_id,
                username
            FROM users
            WHERE user_id NOT IN ({placeholders})
            ORDER BY started_at DESC
            """,
            OWNER_IDS,
        ).fetchall()


        return [
            (
                row["user_id"],
                row["username"],
            )
            for row in rows
        ]

def activate_subscription(
    user_id,
    until,
    tariff,
    subscription_id=None,
):

    with get_db() as db:

        db.execute(
            """
            UPDATE users

            SET
                is_subscribed = TRUE,
                subscribed_until = ?,
                tariff = ?,
                subscription_id = ?

            WHERE user_id = ?
            """,
            (
                until,
                tariff,
                subscription_id,
                user_id,
            ),
        )


        # Удаляем тег без подписки
        db.execute("""
            DELETE FROM user_tags
            WHERE user_id = ?
            AND tag_id IN (
                SELECT id FROM tags
                WHERE name = '#без_подписки'
            )
        """, (user_id,))

        # Удаляем старые теги тарифов
        db.execute("""
            DELETE FROM user_tags
            WHERE user_id = ?
            AND tag_id IN (
                SELECT id FROM tags
                WHERE name IN (
                    '#recurring',
                    '#one_time',
                    '#trial'
                )
            )
        """, (user_id,))

        # Создаём тег нового тарифа
        tag = normalize_tag(tariff)

        db.execute("""
            INSERT OR IGNORE INTO tags (name)
            VALUES (?)
        """, (tag,))

        # Привязываем тег к пользователю
        db.execute("""
            INSERT OR IGNORE INTO user_tags
                (user_id, tag_id)
            SELECT ?, id
            FROM tags
            WHERE name = ?
        """, (user_id, tag))

        db.commit()


def update_subscription_end(
    user_id,
    until,
):

    with get_db() as db:

        db.execute(
            """
            UPDATE users

            SET
                subscribed_until = ?

            WHERE user_id = ?
            """,
            (
                until,
                user_id,
            ),
        )

        db.commit()



def get_subscription_end(user_id):

    with get_db() as db:

        row = db.execute(
            """
            SELECT subscribed_until
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        ).fetchone()


        if not row:
            return None


        if not row["subscribed_until"]:
            return None


        return datetime.strptime(
            row["subscribed_until"],
            "%Y-%m-%d %H:%M:%S"
        )



def get_subscription_id(user_id):

    with get_db() as db:

        row = db.execute(
            """
            SELECT subscription_id
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        ).fetchone()


        if not row:
            return None


        return row["subscription_id"]



def get_user_tariff(user_id):

    with get_db() as db:

        row = db.execute(
            """
            SELECT tariff
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        ).fetchone()


        if not row:
            return None


        return row["tariff"]



def is_subscribed(user_id):

    with get_db() as db:

        row = db.execute(
            """
            SELECT is_subscribed
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        ).fetchone()


        return bool(row and row["is_subscribed"])


def get_subscription_status():

    with get_db() as db:

        now = datetime.now().replace(
            second=0,
            microsecond=0
        )

        expired = db.execute(
            """
            SELECT user_id, tariff
            FROM users
            WHERE
                is_subscribed = TRUE
                AND delete_on_expiration = TRUE
                AND datetime(subscribed_until)
                <= datetime(?)
            """,
            (
                now.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        ).fetchall()

        reminder_time = (
            now + timedelta(days=2)
        )

        reminder = db.execute(
            """
            SELECT user_id, tariff
            FROM users
            WHERE
                is_subscribed = TRUE
                AND delete_on_expiration = TRUE
                AND strftime('%Y-%m-%d %H:%M',
                subscribed_until)
                =
                strftime('%Y-%m-%d %H:%M',
                ?)
            """,
            (
                reminder_time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            ),
        ).fetchall()

        return (
            [
                {
                    "user_id": row["user_id"],
                    "tariff": row["tariff"],
                }
                for row in expired
            ],
            [
                {
                    "user_id": row["user_id"],
                    "tariff": row["tariff"],
                }
                for row in reminder
            ],
        )



def get_subscription_info(user_id):

    with get_db() as db:

        row = db.execute(
            """
            SELECT
                is_subscribed,
                subscribed_until,
                tariff

            FROM users

            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        ).fetchone()


        if not row:
            return None


        if not row["is_subscribed"]:
            return {
                "is_subscribed": False
            }


        until = datetime.strptime(
            row["subscribed_until"],
            "%Y-%m-%d %H:%M:%S"
        )


        days_left = max(
            0,
            (
                until.date()
                -
                datetime.now().date()
            ).days
        )


        return {
            "is_subscribed": True,
            "until": until.strftime(
                "%d.%m.%Y %H:%M"
            ),
            "days_left": days_left,
            "tariff": row["tariff"],
        }

def deactivate_subscription(user_id):

    with get_db() as db:

        db.execute(
            """
            UPDATE users

            SET
                is_subscribed = FALSE,
                subscribed_until = NULL,
                tariff = NULL,
                subscription_id = NULL

            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        )

        
        # Удаляем теги тарифов
        db.execute("""
            DELETE FROM user_tags
            WHERE user_id = ?
            AND tag_id IN (
                SELECT id FROM tags
                WHERE name IN (
                    '#trial',
                    '#recurring',
                    '#one_time'
                )
            )
        """, (user_id,))

        # Создаём тег без подписки
        db.execute("""
            INSERT OR IGNORE INTO tags (name)
            VALUES ('#без_подписки')
        """)

        db.execute("""
            INSERT OR IGNORE INTO user_tags
                (user_id, tag_id)
            SELECT ?, id
            FROM tags
            WHERE name = '#без_подписки'
        """, (user_id,))

        db.commit()

def has_used_trial(user_id):

    with get_db() as db:

        row = db.execute(
            """
            SELECT trial_used
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        ).fetchone()


        return bool(
            row and row["trial_used"]
        )



def mark_trial_used(user_id):

    with get_db() as db:

        db.execute(
            """
            UPDATE users

            SET trial_used = TRUE

            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        )

        db.commit()




def normalize_tag(tag):
    tag = tag.strip().lower().replace(" ", "_")

    if not tag.startswith("#"):
        tag = f"#{tag}"

    return tag


def add_user_tag(user_id, tag):

    tag = normalize_tag(tag)

    with get_db() as db:

        db.execute(
            """
            INSERT OR IGNORE INTO tags (name)
            VALUES (?)
            """,
            (tag,),
        )

        row = db.execute(
            """
            SELECT id
            FROM tags
            WHERE name = ?
            """,
            (tag,),
        ).fetchone()

        db.execute(
            """
            INSERT OR IGNORE INTO user_tags
                (user_id, tag_id)
            VALUES (?, ?)
            """,
            (user_id, row["id"]),
        )

        db.commit()


def add_user_tag_by_id(user_id, tag_id):

    with get_db() as db:

        db.execute(
            """
            INSERT OR IGNORE INTO user_tags
                (user_id, tag_id)
            SELECT ?, id
            FROM tags
            WHERE id = ?
            """,
            (user_id, tag_id),
        )

        db.commit()


def remove_user_tag(user_id, tag):

    tag = normalize_tag(tag)

    with get_db() as db:

        db.execute(
            """
            DELETE FROM user_tags
            WHERE user_id = ?
            AND tag_id = (
                SELECT id FROM tags
                WHERE name = ?
            )
            """,
            (user_id, tag),
        )

        db.commit()


def remove_user_tag_by_id(user_id, tag_id):

    with get_db() as db:

        db.execute(
            """
            DELETE FROM user_tags
            WHERE user_id = ?
            AND tag_id = ?
            """,
            (user_id, tag_id),
        )

        db.commit()


def get_user_tags(user_id):

    with get_db() as db:

        rows = db.execute(
            """
            SELECT tags.name
            FROM tags
            INNER JOIN user_tags
                ON tags.id = user_tags.tag_id
            WHERE user_tags.user_id = ?
            ORDER BY tags.name
            """,
            (user_id,),
        ).fetchall()

        return [row["name"] for row in rows]


def get_all_tags():

    with get_db() as db:

        rows = db.execute(
            """
            SELECT
                tags.name,
                COUNT(user_tags.user_id) AS user_count
            FROM tags
            LEFT JOIN user_tags
                ON tags.id = user_tags.tag_id
            GROUP BY tags.id
            ORDER BY tags.name
            """
        ).fetchall()

        return [
            (row["name"], row["user_count"])
            for row in rows
        ]


def get_all_tags_with_ids():

    with get_db() as db:

        rows = db.execute(
            """
            SELECT
                tags.id,
                tags.name,
                COUNT(user_tags.user_id) AS user_count
            FROM tags
            LEFT JOIN user_tags
                ON tags.id = user_tags.tag_id
            GROUP BY tags.id
            ORDER BY tags.name
            """
        ).fetchall()

        return [
            (
                row["id"],
                row["name"],
                row["user_count"],
            )
            for row in rows
        ]


def get_tag_by_id(tag_id):

    with get_db() as db:

        row = db.execute(
            """
            SELECT name
            FROM tags
            WHERE id = ?
            """,
            (tag_id,),
        ).fetchone()

        return row["name"] if row else None


def get_users_by_tag(tag):

    with get_db() as db:

        rows = db.execute(
            """
            SELECT
                users.user_id,
                users.username
            FROM users
            INNER JOIN user_tags
                ON users.user_id = user_tags.user_id
            INNER JOIN tags
                ON tags.id = user_tags.tag_id
            WHERE tags.name = ?
            ORDER BY users.started_at DESC
            """,
            (normalize_tag(tag),),
        ).fetchall()

        return [
            (row["user_id"], row["username"])
            for row in rows
        ]


def get_users_by_tag_id(tag_id):

    with get_db() as db:

        rows = db.execute(
            """
            SELECT
                users.user_id,
                users.username
            FROM users
            INNER JOIN user_tags
                ON users.user_id = user_tags.user_id
            WHERE user_tags.tag_id = ?
            ORDER BY users.started_at DESC
            """,
            (tag_id,),
        ).fetchall()

        return [
            (row["user_id"], row["username"])
            for row in rows
        ]


def get_delete_on_expiration(user_id):
    """
    Return whether the user should be deleted
    when their subscription expires.
    """
    with get_db() as db:

        row = db.execute(
            """
            SELECT delete_on_expiration
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        ).fetchone()

        if not row:
            return None

        return bool(row["delete_on_expiration"])


def set_delete_on_expiration(user_id, enabled):
    """
    Enable or disable deletion of the user
    when their subscription expires.
    """
    with get_db() as db:

        db.execute(
            """
            UPDATE users

            SET delete_on_expiration = ?

            WHERE user_id = ?
            """,
            (
                bool(enabled),
                user_id,
            ),
        )

        db.commit()


def toggle_delete_on_expiration(user_id):
    """
    Toggle the user's delete_on_expiration setting.

    Returns the new value.
    """
    with get_db() as db:

        row = db.execute(
            """
            SELECT delete_on_expiration
            FROM users
            WHERE user_id = ?
            """,
            (
                user_id,
            ),
        ).fetchone()

        if not row:
            return None

        new_value = not bool(row["delete_on_expiration"])

        db.execute(
            """
            UPDATE users

            SET delete_on_expiration = ?

            WHERE user_id = ?
            """,
            (
                new_value,
                user_id,
            ),
        )

        db.commit()

        return new_value


selected_conversations = {}
