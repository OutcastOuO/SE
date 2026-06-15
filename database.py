import sqlite3
import hashlib
from datetime import datetime, timedelta

from config import DB_PATH

DB_NAME = str(DB_PATH)


def _connect():
    return sqlite3.connect(DB_NAME)


def _now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _table_columns(cur, table_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cur.fetchall()]


def _add_column_if_missing(cur, table_name, column_name, column_def):
    columns = _table_columns(cur, table_name)
    if column_name not in columns:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def init_db():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        plate_no TEXT PRIMARY KEY,
        material_type TEXT NOT NULL DEFAULT 'A',
        status TEXT NOT NULL DEFAULT 'standby_empty',
        updated_at TEXT,
        eta_time TEXT,
        destination TEXT,
        loading_level TEXT,
        repair_reason TEXT,
        enabled INTEGER NOT NULL DEFAULT 1
    )
    """)

    # 舊版資料庫若少欄位，這裡自動補欄位。
    _add_column_if_missing(cur, "vehicles", "material_type", "TEXT NOT NULL DEFAULT 'A'")
    _add_column_if_missing(cur, "vehicles", "status", "TEXT NOT NULL DEFAULT 'standby_empty'")
    _add_column_if_missing(cur, "vehicles", "updated_at", "TEXT")
    _add_column_if_missing(cur, "vehicles", "eta_time", "TEXT")
    _add_column_if_missing(cur, "vehicles", "destination", "TEXT")
    _add_column_if_missing(cur, "vehicles", "out_start_time", "TEXT")
    _add_column_if_missing(cur, "vehicles", "loading_level", "TEXT")
    _add_column_if_missing(cur, "vehicles", "repair_reason", "TEXT")
    _add_column_if_missing(cur, "vehicles", "enabled", "INTEGER NOT NULL DEFAULT 1")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS destinations (
        destination_name TEXT PRIMARY KEY,
        hours REAL NOT NULL DEFAULT 1,
        enabled INTEGER NOT NULL DEFAULT 1
    )
    """)

    _add_column_if_missing(cur, "destinations", "hours", "REAL NOT NULL DEFAULT 1")
    _add_column_if_missing(cur, "destinations", "enabled", "INTEGER NOT NULL DEFAULT 1")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS loading_levels (
        level_name TEXT PRIMARY KEY,
        hours REAL NOT NULL DEFAULT 0.5,
        enabled INTEGER NOT NULL DEFAULT 1
    )
    """)

    _add_column_if_missing(cur, "loading_levels", "hours", "REAL NOT NULL DEFAULT 0.5")
    _add_column_if_missing(cur, "loading_levels", "enabled", "INTEGER NOT NULL DEFAULT 1")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        login_account TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'viewer',
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """)

    _add_column_if_missing(cur, "users", "display_name", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(cur, "users", "password", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(cur, "users", "role", "TEXT NOT NULL DEFAULT 'viewer'")
    _add_column_if_missing(cur, "users", "is_active", "INTEGER NOT NULL DEFAULT 1")

    # 新增：出差目的地 × 車牌白名單
    cur.execute("""
    CREATE TABLE IF NOT EXISTS destination_car_whitelist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destination_name TEXT NOT NULL,
        car_no TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        UNIQUE(destination_name, car_no)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trip_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_no TEXT NOT NULL,
        destination TEXT,
        out_start_time TEXT,
        eta_time TEXT,
        actual_finish_time TEXT NOT NULL,
        to_status TEXT NOT NULL,
        recorded_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trip_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_no TEXT NOT NULL,
        destination TEXT,
        out_start_time TEXT,
        eta_time TEXT,
        actual_finish_time TEXT NOT NULL,
        to_status TEXT NOT NULL,
        recorded_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def seed_sample_data():
    """
    第一次開啟時建立基本測試資料。
    若資料表已有資料，不會覆蓋。
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM vehicles")
    vehicle_count = cur.fetchone()[0]

    if vehicle_count == 0:
        sample_vehicles = [
            ("662", "A", "standby_empty"),
            ("790", "A", "standby_full"),
            ("888", "B", "standby_empty"),
            ("999", "B", "standby_full"),
        ]

        for plate_no, material_type, status in sample_vehicles:
            cur.execute("""
                INSERT OR IGNORE INTO vehicles
                    (plate_no, material_type, status, updated_at, enabled)
                VALUES (?, ?, ?, ?, 1)
            """, (plate_no, material_type, status, _now_text()))

    cur.execute("SELECT COUNT(*) FROM destinations")
    destination_count = cur.fetchone()[0]

    if destination_count == 0:
        sample_destinations = [
            ("台積電", 2.0),
            ("林園廠", 1.0),
            ("南科", 2.5),
        ]

        for name, hours in sample_destinations:
            cur.execute("""
                INSERT OR IGNORE INTO destinations
                    (destination_name, hours, enabled)
                VALUES (?, ?, 1)
            """, (name, hours))

    cur.execute("SELECT COUNT(*) FROM loading_levels")
    loading_count = cur.fetchone()[0]

    if loading_count == 0:
        sample_loading = [
            ("低液位", 0.5),
            ("中液位", 1.0),
            ("高液位", 1.5),
        ]

        for level, hours in sample_loading:
            cur.execute("""
                INSERT OR IGNORE INTO loading_levels
                    (level_name, hours, enabled)
                VALUES (?, ?, 1)
            """, (level, hours))

    conn.commit()
    conn.close()


def reset_sample_data():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM destination_car_whitelist")
    cur.execute("DELETE FROM vehicles")
    cur.execute("DELETE FROM destinations")
    cur.execute("DELETE FROM loading_levels")

    sample_vehicles = [
        ("662", "A", "standby_empty"),
        ("790", "A", "standby_full"),
        ("888", "B", "standby_empty"),
        ("999", "B", "standby_full"),
    ]

    for plate_no, material_type, status in sample_vehicles:
        cur.execute("""
            INSERT INTO vehicles
                (plate_no, material_type, status, updated_at, eta_time, destination, loading_level, repair_reason, enabled)
            VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, 1)
        """, (plate_no, material_type, status, _now_text()))

    sample_destinations = [
        ("台積電", 2.0),
        ("林園廠", 1.0),
        ("南科", 2.5),
    ]

    for name, hours in sample_destinations:
        cur.execute("""
            INSERT INTO destinations
                (destination_name, hours, enabled)
            VALUES (?, ?, 1)
        """, (name, hours))

    sample_loading = [
        ("低液位", 0.5),
        ("中液位", 1.0),
        ("高液位", 1.5),
    ]

    for level, hours in sample_loading:
        cur.execute("""
            INSERT INTO loading_levels
                (level_name, hours, enabled)
            VALUES (?, ?, 1)
        """, (level, hours))

    conn.commit()
    conn.close()


def get_vehicles():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            plate_no,
            material_type,
            status,
            updated_at,
            eta_time,
            destination,
            loading_level,
            repair_reason
        FROM vehicles
        WHERE enabled = 1
        ORDER BY material_type, plate_no
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def add_vehicle(plate_no, material_type):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO vehicles
            (plate_no, material_type, status, updated_at, eta_time, destination, loading_level, repair_reason, enabled)
        VALUES (?, ?, 'standby_empty', ?, NULL, NULL, NULL, NULL, 1)
    """, (str(plate_no).strip(), str(material_type).strip(), _now_text()))

    conn.commit()
    conn.close()


def update_vehicle(old_plate_no, new_plate_no, material_type):
    old_plate_no = str(old_plate_no).strip()
    new_plate_no = str(new_plate_no).strip()
    material_type = str(material_type).strip()

    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE vehicles
        SET plate_no = ?,
            material_type = ?,
            updated_at = ?
        WHERE plate_no = ?
    """, (new_plate_no, material_type, _now_text(), old_plate_no))

    # 車牌改名時，同步更新白名單。
    cur.execute("""
        UPDATE destination_car_whitelist
        SET car_no = ?
        WHERE car_no = ?
    """, (new_plate_no, old_plate_no))

    conn.commit()
    conn.close()


def delete_vehicle(plate_no):
    plate_no = str(plate_no).strip()

    conn = _connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM destination_car_whitelist WHERE car_no = ?", (plate_no,))
    cur.execute("DELETE FROM vehicles WHERE plate_no = ?", (plate_no,))

    conn.commit()
    conn.close()


def update_vehicle_status(plate_no, status):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE vehicles
        SET status = ?,
            updated_at = ?,
            eta_time = NULL,
            destination = NULL,
            loading_level = NULL,
            repair_reason = NULL
        WHERE plate_no = ?
    """, (status, _now_text(), str(plate_no).strip()))

    conn.commit()
    conn.close()


def update_vehicle_out(plate_no, destination, hours, out_start_time=None):
    """
    車輛進入出差中。
    out_start_time 用來記錄 Excel A欄的出差時間。
    """
    eta_time = datetime.now() + timedelta(hours=float(hours))

    if out_start_time is None or str(out_start_time).strip() == "":
        out_start_time = _now_text()

    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE vehicles
        SET status = 'out',
            updated_at = ?,
            out_start_time = ?,
            eta_time = ?,
            destination = ?,
            loading_level = NULL,
            repair_reason = NULL
        WHERE plate_no = ?
    """, (
        _now_text(),
        str(out_start_time).strip(),
        eta_time.strftime("%Y-%m-%d %H:%M:%S"),
        str(destination).strip(),
        str(plate_no).strip(),
    ))

    conn.commit()
    conn.close()


def update_vehicle_loading(plate_no, level, loading_minutes):
    eta_time = datetime.now() + timedelta(minutes=float(loading_minutes))

    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE vehicles
        SET status = 'loading',
            updated_at = ?,
            eta_time = ?,
            destination = NULL,
            loading_level = ?,
            repair_reason = NULL
        WHERE plate_no = ?
    """, (
        _now_text(),
        eta_time.strftime("%Y-%m-%d %H:%M:%S"),
        str(level).strip(),
        str(plate_no).strip(),
    ))

    conn.commit()
    conn.close()


def update_vehicle_repair(plate_no, reason):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE vehicles
        SET status = 'repair',
            updated_at = ?,
            eta_time = NULL,
            destination = NULL,
            loading_level = NULL,
            repair_reason = ?
        WHERE plate_no = ?
    """, (_now_text(), str(reason).strip(), str(plate_no).strip()))

    conn.commit()
    conn.close()


def get_destinations():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT destination_name, hours
        FROM destinations
        WHERE enabled = 1
        ORDER BY destination_name
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def add_destination(destination_name, hours):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO destinations
            (destination_name, hours, enabled)
        VALUES (?, ?, 1)
    """, (str(destination_name).strip(), float(hours)))

    conn.commit()
    conn.close()


def update_destination(old_name, new_name, hours):
    old_name = str(old_name).strip()
    new_name = str(new_name).strip()

    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE destinations
        SET destination_name = ?,
            hours = ?
        WHERE destination_name = ?
    """, (new_name, float(hours), old_name))

    # 目的地改名時，同步更新白名單與車輛目前目的地。
    cur.execute("""
        UPDATE destination_car_whitelist
        SET destination_name = ?
        WHERE destination_name = ?
    """, (new_name, old_name))

    cur.execute("""
        UPDATE vehicles
        SET destination = ?
        WHERE destination = ?
    """, (new_name, old_name))

    conn.commit()
    conn.close()


def delete_destination(destination_name):
    destination_name = str(destination_name).strip()

    conn = _connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM destination_car_whitelist WHERE destination_name = ?", (destination_name,))
    cur.execute("DELETE FROM destinations WHERE destination_name = ?", (destination_name,))

    conn.commit()
    conn.close()


def get_destination_minutes(destination_name):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT hours
        FROM destinations
        WHERE destination_name = ?
          AND enabled = 1
    """, (str(destination_name).strip(),))

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return float(row[0]) * 60


def get_loading_levels():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT level_name, hours
        FROM loading_levels
        WHERE enabled = 1
        ORDER BY level_name
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def add_loading_level(level_name, hours):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO loading_levels
            (level_name, hours, enabled)
        VALUES (?, ?, 1)
    """, (str(level_name).strip(), float(hours)))

    conn.commit()
    conn.close()


def update_loading_level(old_level, new_level, hours):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE loading_levels
        SET level_name = ?,
            hours = ?
        WHERE level_name = ?
    """, (str(new_level).strip(), float(hours), str(old_level).strip()))

    cur.execute("""
        UPDATE vehicles
        SET loading_level = ?
        WHERE loading_level = ?
    """, (str(new_level).strip(), str(old_level).strip()))

    conn.commit()
    conn.close()


def delete_loading_level(level_name):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM loading_levels WHERE level_name = ?", (str(level_name).strip(),))

    conn.commit()
    conn.close()


def seed_default_admin():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users
            (login_account, display_name, password, role, is_active)
        VALUES ('admin', '管理員', '1234', 'admin', 1)
        ON CONFLICT(login_account)
        DO UPDATE SET
            display_name = '管理員',
            password = '1234',
            role = 'admin',
            is_active = 1
    """)


    conn.commit()
    conn.close()


def authenticate_user(login_account, password):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT login_account, display_name, role
        FROM users
        WHERE login_account = ?
          AND password = ?
          AND is_active = 1
    """, (str(login_account).strip(), str(password).strip()))

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "login_account": row[0],
        "display_name": row[1],
        "role": row[2],
    }


def get_users():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT login_account, display_name, role, is_active
        FROM users
        ORDER BY login_account
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def add_user(login_account, display_name, password, role):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users
            (login_account, display_name, password, role, is_active)
        VALUES (?, ?, ?, ?, 1)
    """, (
        str(login_account).strip(),
        str(display_name).strip(),
        str(password).strip(),
        str(role).strip(),
    ))

    conn.commit()
    conn.close()


def update_user(old_login, new_login, display_name, password, role, is_active):
    old_login = str(old_login).strip()
    new_login = str(new_login).strip()
    display_name = str(display_name).strip()
    role = str(role).strip()
    is_active = int(is_active)

    conn = _connect()
    cur = conn.cursor()

    if password is None or str(password).strip() == "":
        cur.execute("""
            UPDATE users
            SET login_account = ?,
                display_name = ?,
                role = ?,
                is_active = ?
            WHERE login_account = ?
        """, (new_login, display_name, role, is_active, old_login))
    else:
        cur.execute("""
            UPDATE users
            SET login_account = ?,
                display_name = ?,
                password = ?,
                role = ?,
                is_active = ?
            WHERE login_account = ?
        """, (
            new_login,
            display_name,
            str(password).strip(),
            role,
            is_active,
            old_login,
        ))

    conn.commit()
    conn.close()


def delete_user(login_account):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM users WHERE login_account = ?", (str(login_account).strip(),))

    conn.commit()
    conn.close()


def get_all_enabled_car_nos():
    """
    設定畫面中，出差目的地底下的車牌 checkbox 來源。
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT plate_no
        FROM vehicles
        WHERE enabled = 1
        ORDER BY plate_no
    """)

    rows = cur.fetchall()
    conn.close()
    return [str(row[0]) for row in rows]


def get_destination_whitelist(destination_name):
    """
    取得某目的地已勾選的車牌白名單。
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT car_no
        FROM destination_car_whitelist
        WHERE destination_name = ?
          AND enabled = 1
        ORDER BY car_no
    """, (str(destination_name).strip(),))

    rows = cur.fetchall()
    conn.close()
    return [str(row[0]) for row in rows]


def set_destination_whitelist(destination_name, selected_car_nos):
    """
    儲存某目的地允許出差的車牌。
    """
    destination_name = str(destination_name).strip()

    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM destination_car_whitelist
        WHERE destination_name = ?
    """, (destination_name,))

    for car_no in selected_car_nos:
        cur.execute("""
            INSERT INTO destination_car_whitelist
                (destination_name, car_no, enabled)
            VALUES (?, ?, 1)
        """, (destination_name, str(car_no).strip()))

    conn.commit()
    conn.close()


def is_car_allowed_for_destination(destination_name, car_no):
    """
    有勾選才回傳 True；沒勾選、沒設定、非白名單都回傳 False。
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM destination_car_whitelist
        WHERE destination_name = ?
          AND car_no = ?
          AND enabled = 1
    """, (str(destination_name).strip(), str(car_no).strip()))

    count = cur.fetchone()[0]
    conn.close()
    return count > 0

def complete_vehicle_out(plate_no, to_status, actual_finish_time):
    """
    車輛從「出差中」移出時使用：
    1. 先把目前出差資料寫入 trip_records
    2. 再把車輛移到新的狀態
    """

    plate_no = str(plate_no).strip()
    to_status = str(to_status).strip()
    actual_finish_time = str(actual_finish_time).strip()

    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT destination, eta_time, updated_at
        FROM vehicles
        WHERE plate_no = ?
    """, (plate_no,))

    row = cur.fetchone()

    if row is None:
        conn.close()
        raise Exception(f"找不到車牌：{plate_no}")

    destination, eta_time, out_start_time = row

    now_text = _now_text()

    cur.execute("""
        INSERT INTO trip_records
            (plate_no, destination, out_start_time, eta_time,
             actual_finish_time, to_status, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        plate_no,
        destination,
        out_start_time,
        eta_time,
        actual_finish_time,
        to_status,
        now_text,
    ))

    cur.execute("""
        UPDATE vehicles
        SET status = ?,
            updated_at = ?,
            eta_time = NULL,
            destination = NULL,
            loading_level = NULL,
            repair_reason = NULL
        WHERE plate_no = ?
    """, (
        to_status,
        now_text,
        plate_no,
    ))

    conn.commit()
    conn.close()

def complete_vehicle_out(plate_no, to_status, actual_finish_time):
    """
    車輛從出差中移出時：
    1. 寫入 trip_records
    2. 再把車輛移到目標狀態
    """
    plate_no = str(plate_no).strip()
    to_status = str(to_status).strip()
    actual_finish_time = str(actual_finish_time).strip()

    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT destination, eta_time, out_start_time, updated_at
        FROM vehicles
        WHERE plate_no = ?
    """, (plate_no,))

    row = cur.fetchone()

    if row is None:
        conn.close()
        raise Exception(f"找不到車牌：{plate_no}")

    destination, eta_time, out_start_time, updated_at = row

    if out_start_time is None or str(out_start_time).strip() == "":
        out_start_time = updated_at

    recorded_at = _now_text()

    cur.execute("""
        INSERT INTO trip_records
            (plate_no, destination, out_start_time, eta_time,
             actual_finish_time, to_status, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        plate_no,
        destination,
        out_start_time,
        eta_time,
        actual_finish_time,
        to_status,
        recorded_at,
    ))

    cur.execute("""
        UPDATE vehicles
        SET status = ?,
            updated_at = ?,
            out_start_time = NULL,
            eta_time = NULL,
            destination = NULL,
            loading_level = NULL,
            repair_reason = NULL
        WHERE plate_no = ?
    """, (
        to_status,
        recorded_at,
        plate_no,
    ))

    conn.commit()
    conn.close()


def get_trip_records_for_export(start_time=None, end_time=None):
    """
    匯出用：
    依照實際完成時間 actual_finish_time 篩選。
    start_time / end_time 格式：YYYY-MM-DD HH:MM:SS
    """
    conn = _connect()
    cur = conn.cursor()

    if start_time and end_time:
        cur.execute("""
            SELECT plate_no, destination, out_start_time, actual_finish_time
            FROM trip_records
            WHERE actual_finish_time >= ?
              AND actual_finish_time <= ?
            ORDER BY actual_finish_time DESC, id DESC
        """, (start_time, end_time))

    elif start_time:
        cur.execute("""
            SELECT plate_no, destination, out_start_time, actual_finish_time
            FROM trip_records
            WHERE actual_finish_time >= ?
            ORDER BY actual_finish_time DESC, id DESC
        """, (start_time,))

    elif end_time:
        cur.execute("""
            SELECT plate_no, destination, out_start_time, actual_finish_time
            FROM trip_records
            WHERE actual_finish_time <= ?
            ORDER BY actual_finish_time DESC, id DESC
        """, (end_time,))

    else:
        cur.execute("""
            SELECT plate_no, destination, out_start_time, actual_finish_time
            FROM trip_records
            ORDER BY actual_finish_time DESC, id DESC
        """)

    rows = cur.fetchall()
    conn.close()
    return rows


def get_vehicle_by_plate(plate_no):
    """取得單一車輛資料，回傳 dict 或 None。"""
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            plate_no, material_type, status,
            updated_at, eta_time, destination,
            loading_level, repair_reason
        FROM vehicles
        WHERE plate_no = ? AND enabled = 1
    """, (str(plate_no).strip(),))

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "plate_no": row[0],
        "material_type": row[1],
        "status": row[2],
        "updated_at": row[3],
        "eta_time": row[4],
        "destination": row[5],
        "loading_level": row[6],
        "repair_reason": row[7],
    }


def batch_update_vehicle_status(plate_nos, status):
    """批次更新多台車輛狀態（chaos testing 用）。"""
    conn = _connect()
    cur = conn.cursor()
    now = _now_text()

    for plate_no in plate_nos:
        cur.execute("""
            UPDATE vehicles
            SET status = ?,
                updated_at = ?,
                eta_time = NULL,
                destination = NULL,
                loading_level = NULL,
                repair_reason = NULL
            WHERE plate_no = ? AND enabled = 1
        """, (status, now, str(plate_no).strip()))

    conn.commit()
    conn.close()
    return len(plate_nos)