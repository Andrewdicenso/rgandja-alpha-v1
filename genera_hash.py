import bcrypt

password_da_usare = "LA_TUA_PASSWORD_SCELTA"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password_da_usare.encode('utf-8'), salt)

print(f"Ecco l'hash da copiare nel database: {hashed.decode('utf-8')}")