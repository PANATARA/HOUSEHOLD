import re

PASSWORD_PATTERN = re.compile(r"^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$")
LETTER_MATCH_PATTERN = re.compile(r"^[а-яА-Яa-zA-Z\-]+$")
