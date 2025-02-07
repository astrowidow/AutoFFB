from AutoFFB import *

vpn_manager = VpnManager()
vpn_manager.enable(True)

login_manager = LoginManager()
login_manager.add_account("04:00", "id", "pass")
login_manager.add_account("16:00", "id", "pass")

notifier = Notifier()
notifier.add_webhook("hook url")

# 鎧集めなし、各種鉱石集め
Macro.collect_material("manomori", collect_yoroi=False, collect_various_kouseki=True)

# # 鎧集めなし、白Only
# Macro.collect_material("manomori", collect_yoroi=False, collect_various_kouseki=False)

# # 鎧集めあり、各種鉱石集め
# Macro.collect_material("manomori", collect_yoroi=True, collect_various_kouseki=True)


