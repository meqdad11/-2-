def estimate_telegram_registration(user_id: int) -> str:
    """تقدير تاريخ التسجيل في تليجرام"""
    if user_id < 100_000_000:
        return "~2015"
    elif user_id < 200_000_000:
        return "~2016"
    elif user_id < 300_000_000:
        return "~2017"
    elif user_id < 400_000_000:
        return "~2018"
    elif user_id < 500_000_000:
        return "~2019"
    elif user_id < 600_000_000:
        return "~2020"
    elif user_id < 700_000_000:
        return "~2021"
    elif user_id < 800_000_000:
        return "~2022"
    elif user_id < 900_000_000:
        return "~2023"
    elif user_id < 1_000_000_000:
        return "~2024"
    elif user_id < 1_100_000_000:
        return "~2025"
    else:
        return "~2026"
