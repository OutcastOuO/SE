from pathlib import Path
import configparser
import os
import sys


def get_app_dir():
    """
    開發階段：回傳 .py 所在資料夾
    打包成 exe 後：回傳 VMS.exe 所在資料夾
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()

config = configparser.ConfigParser()
config_path = APP_DIR / "config.ini"

env_data_dir = os.getenv("VMS_DATA_DIR")

if env_data_dir:
    data_dir_text = env_data_dir
elif config_path.exists():
    config.read(config_path, encoding="utf-8")
    data_dir_text = config.get(
        "PATH",
        "DATA_DIR",
        fallback=str(APP_DIR.parent / "VMS_Data"),
    )
else:
    data_dir_text = str(APP_DIR.parent / "VMS_Data")

DATA_DIR = Path(data_dir_text)

DB_PATH = DATA_DIR / "vms.db"
TRIP_EXCEL_PATH = DATA_DIR / "出差資料.xlsx"
DAILY_EXPORT_DIR = DATA_DIR / "每日自動匯出"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DAILY_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
