from AutoFFB import *

account_info = AccountInfo()


html_content = pyperclip.paste()
count = account_info.parse_penalty_count(html_content)

print(count)
