import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from config import OWNER_IDS


DATABASE = "bot.db"


@contextmanager
def get_db():

    conn = sqlite3.connect(
        DATABASE,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()



def init_db():

    with get_db() as db:

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_subscribed BOOLEAN DEFAULT FALSE,
                subscribed_until TIMESTAMP DEFAULT NULL,
                tariff TEXT DEFAULT NULL,
                trial_used BOOLEAN DEFAULT FALSE,
                subscription_id TEXT DEFAULT NULL
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS tags(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_tags(
                user_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,

                PRIMARY KEY(user_id, tag_id),

                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,

                FOREIGN KEY(tag_id)
                    REFERENCES tags(id)
                    ON DELETE CASCADE
            )
            """
        )

        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_tags_tag
            ON user_tags(tag_id)
            """
        )

        db.commit()



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
            SELECT user_id
            FROM users
            WHERE
                is_subscribed = TRUE
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
            SELECT user_id
            FROM users
            WHERE
                is_subscribed = TRUE
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
                row["user_id"]
                for row in expired
            ],
            [
                row["user_id"]
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

def add_tag(name):

    with get_db() as db:

        db.execute(
            """
            INSERT OR IGNORE INTO tags(name)
            VALUES(?)
            """,
            (
                name.lower(),
            ),
        )

        db.commit()

def add_user_tag(
    user_id,
    tag_id,
):

    with get_db() as db:

        db.execute(
            """
            INSERT OR IGNORE INTO user_tags(
                user_id,
                tag_id
            )
            VALUES(?, ?)
            """,
            (
                user_id,
                tag_id,
            ),
        )

        db.commit()


def remove_user_tag(
    user_id,
    tag_id,
):

    with get_db() as db:

        db.execute(
            """
            DELETE FROM user_tags

            WHERE
                user_id = ?
                AND tag_id = ?
            """,
            (
                user_id,
                tag_id,
            ),
        )

        db.commit()


def get_user_tags(user_id):

    with get_db() as db:

        rows = db.execute(
            """
            SELECT
                t.id,
                t.name

            FROM tags t

            JOIN user_tags ut
                ON ut.tag_id = t.id

            WHERE ut.user_id = ?

            ORDER BY t.name
            """,
            (
                user_id,
            ),
        ).fetchall()

        return [
            (
                row["id"],
                row["name"],
            )
            for row in rows
        ]

def get_users_by_tag(tag_id):

    with get_db() as db:

        rows = db.execute(
            """
            SELECT
                user_id

            FROM user_tags

            WHERE tag_id = ?
            """,
            (
                tag_id,
            ),
        ).fetchall()

        return [
            row["user_id"]
            for row in rows
        ]

def get_all_tags():

    with get_db() as db:

        rows = db.execute(
            """
            SELECT
                id,
                name

            FROM tags

            ORDER BY name
            """
        ).fetchall()

        return [
            (
                row["id"],
                row["name"],
            )
            for row in rows
        ]

def get_tag(tag_id):

    with get_db() as db:

        return db.execute(
            """
            SELECT
                id,
                name

            FROM tags

            WHERE id = ?
            """,
            (
                tag_id,
            ),
        ).fetchone()

def delete_tag(tag_id):

    with get_db() as db:

        db.execute(
            """
            DELETE FROM tags
            WHERE id = ?
            """,
            (
                tag_id,
            ),
        )

        db.commit()

selected_conversations = {}