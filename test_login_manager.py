from AutoFFB import *

login_manager = LoginManager()
login_manager.add_account("04:00", "id", "pass")
login_manager.add_account("05:00", "id", "pass")
login_manager.add_account("11:05", "id", "pass")
login_manager.add_account("12:00", "id", "pass")
login_manager.add_account("12:10", "id", "pass")

print(login_manager.get_seconds_until_next_switch())
