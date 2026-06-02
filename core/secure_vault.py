from cryptography.fernet import Fernet, InvalidToken
import os
import logging

logger = logging.getLogger("RGD-Alpha.Vault")

class SecureVault:
    """
    Vault aziendale: Cifratura simmetrica AES per la protezione dei dati sensibili.
    Gestisce automaticamente la persistenza della Master Key.
    """
    def __init__(self, key_path="core/security/vault.key"):
        # Normalizziamo il percorso per evitare errori su Windows/Linux
        self.key_path = os.path.abspath(key_path)
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)

    def _load_or_create_key(self) -> bytes:
        """Carica o genera la Master Key con verifica permessi."""
        try:
            folder = os.path.dirname(self.key_path)
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
            
            if os.path.exists(self.key_path):
                with open(self.key_path, "rb") as key_file:
                    key_data = key_file.read()
                    if not key_data:
                        raise ValueError("File chiave vuoto.")
                    return key_data
            else:
                # Generazione nuova chiave se non esiste
                key = Fernet.generate_key()
                with open(self.key_path, "wb") as key_file:
                    key_file.write(key)
                logger.info(f"🛡️ Master Key generata con successo: {self.key_path}")
                return key
        except PermissionError:
            logger.critical(f"❌ ERRORE PERMESSI: Impossibile scrivere in {self.key_path}")
            raise
        except Exception as e:
            logger.critical(f"❌ FALLIMENTO CRITICO SECURITY: {e}")
            raise

    def encrypt_data(self, data: str) -> str:
        """Cifra una stringa e restituisce una stringa sicura per il DB."""
        if data is None: return None
        try:
            # Convertiamo in bytes, cifriamo e torniamo in stringa per SQLite
            return self.cipher.encrypt(data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.error(f"Errore cifratura: {e}")
            raise

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decifra i dati. Accetta stringhe o bytes (massima compatibilità)."""
        if not encrypted_data: return ""
        try:
            # Assicuriamoci di avere bytes per la decifratura
            if isinstance(encrypted_data, str):
                encrypted_data = encrypted_data.encode('utf-8')
            
            return self.cipher.decrypt(encrypted_data).decode('utf-8')
        except InvalidToken:
            logger.error("⚠️ ALERT SICUREZZA: Chiave non valida o dati manomessi!")
            return "ERR_SEC_INVALID_TOKEN"
        except Exception as e:
            logger.error(f"Errore decifratura: {e}")
            return "ERR_SEC_GENERIC"

# --- TEST DI INTEGRITÀ RAPIDO ---
if __name__ == "__main__":
    vault = SecureVault()
    test_msg = "Azienda_Segreta_123"
    criptato = vault.encrypt_data(test_msg)
    decriptato = vault.decrypt_data(criptato)
    
    print(f"Originale: {test_msg}")
    print(f"Criptato: {criptato}")
    print(f"Decriptato correttamente: {test_msg == decriptato}")