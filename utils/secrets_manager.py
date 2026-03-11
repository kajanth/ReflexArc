"""
Secrets management and validation for NSA ReflexArc system.
Handles API key validation, rotation, audit logging, and encrypted storage.
"""

import os
import re
import time
import json
import base64
import hashlib
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

logger = structlog.get_logger(__name__)


class SecretsManager:
    """Manages API keys and secrets for the NSA system."""
    
    def __init__(self):
        self.audit_log_path = Path("memory/secrets_audit.json")
        self.encrypted_store_path = Path("memory/encrypted_secrets.dat")
        self.secrets_cache = {}
        self.last_validation = {}
        self._encryption_key = None
        
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for sensitive data storage."""
        if self._encryption_key:
            return self._encryption_key
            
        # Try to get key from environment
        key_env = os.getenv('NSA_ENCRYPTION_KEY')
        if key_env:
            try:
                self._encryption_key = base64.urlsafe_b64decode(key_env)
                return self._encryption_key
            except Exception as e:
                logger.warning("Invalid encryption key in environment", error=str(e))
        
        # Generate key from system-specific data
        system_data = (
            os.getenv('HOSTNAME', 'localhost') +
            str(os.getuid() if hasattr(os, 'getuid') else 'windows') +
            str(Path.home())
        ).encode()
        
        # Use PBKDF2 to derive key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'nsa_reflexarc_salt_2024',  # Fixed salt for consistency
            iterations=100000,
        )
        self._encryption_key = kdf.derive(system_data)
        return self._encryption_key
    
    def store_encrypted_secret(self, key_name: str, secret_value: str) -> bool:
        """
        Store a secret in encrypted format.
        
        Args:
            key_name: Name of the secret
            secret_value: Value to encrypt and store
            
        Returns:
            True if stored successfully
        """
        try:
            # Load existing encrypted data
            encrypted_data = self._load_encrypted_store()
            
            # Encrypt the secret
            fernet = Fernet(base64.urlsafe_b64encode(self._get_encryption_key()))
            encrypted_value = fernet.encrypt(secret_value.encode())
            
            # Store with metadata
            encrypted_data[key_name] = {
                'value': base64.urlsafe_b64encode(encrypted_value).decode(),
                'created': time.time(),
                'last_accessed': time.time()
            }
            
            # Save to disk
            self._save_encrypted_store(encrypted_data)
            
            logger.info("Secret stored in encrypted format", key_name=key_name)
            self._log_key_usage(key_name, "encrypted_storage")
            return True
            
        except Exception as e:
            logger.error("Failed to store encrypted secret", key_name=key_name, error=str(e))
            return False
    
    def retrieve_encrypted_secret(self, key_name: str) -> Optional[str]:
        """
        Retrieve and decrypt a stored secret.
        
        Args:
            key_name: Name of the secret to retrieve
            
        Returns:
            Decrypted secret value or None if not found
        """
        try:
            encrypted_data = self._load_encrypted_store()
            
            if key_name not in encrypted_data:
                return None
            
            # Decrypt the secret
            fernet = Fernet(base64.urlsafe_b64encode(self._get_encryption_key()))
            encrypted_value = base64.urlsafe_b64decode(encrypted_data[key_name]['value'])
            decrypted_value = fernet.decrypt(encrypted_value).decode()
            
            # Update last accessed time
            encrypted_data[key_name]['last_accessed'] = time.time()
            self._save_encrypted_store(encrypted_data)
            
            self._log_key_usage(key_name, "encrypted_retrieval")
            return decrypted_value
            
        except Exception as e:
            logger.error("Failed to retrieve encrypted secret", key_name=key_name, error=str(e))
            return None
    
    def _load_encrypted_store(self) -> Dict:
        """Load encrypted secrets store."""
        try:
            if self.encrypted_store_path.exists():
                with open(self.encrypted_store_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning("Failed to load encrypted store", error=str(e))
        
        return {}
    
    def _save_encrypted_store(self, data: Dict):
        """Save encrypted secrets store."""
        try:
            # Ensure directory exists
            self.encrypted_store_path.parent.mkdir(exist_ok=True)
            
            with open(self.encrypted_store_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save encrypted store", error=str(e))
        
    def validate_api_keys_on_startup(self) -> Tuple[bool, List[str]]:
        """
        Validate all required API keys are present and properly formatted.
        
        Returns:
            Tuple of (all_valid, error_messages)
        """
        errors = []
        
        # Define required providers and their key patterns
        provider_keys = {
            'OPENAI_API_KEY': {
                'pattern': r'^sk-[a-zA-Z0-9_-]{30,}$',
                'description': 'OpenAI API key'
            },
            'ANTHROPIC_API_KEY': {
                'pattern': r'^sk-ant-[a-zA-Z0-9_-]{95,}$',
                'description': 'Anthropic API key'
            },
            'GOOGLE_API_KEY': {
                'pattern': r'^[a-zA-Z0-9_-]{39}$',
                'description': 'Google Gemini API key'
            }
        }
        
        # AWS keys (all three required together)
        aws_keys = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
        
        # Check if at least one provider is configured
        has_provider = False
        
        for key_name, config in provider_keys.items():
            api_key = os.getenv(key_name)
            
            if api_key:
                has_provider = True
                if not re.match(config['pattern'], api_key):
                    errors.append(f"Invalid format for {config['description']} ({key_name})")
                else:
                    logger.info(f"Valid {config['description']} found")
                    self._log_key_usage(key_name, "validation_success")
            
        # Check AWS configuration (all or none)
        aws_values = [os.getenv(key) for key in aws_keys]
        aws_configured = any(aws_values)
        
        if aws_configured:
            has_provider = True
            missing_aws = [key for key, value in zip(aws_keys, aws_values) if not value]
            if missing_aws:
                errors.append(f"Incomplete AWS configuration. Missing: {', '.join(missing_aws)}")
            else:
                # Validate AWS key formats
                access_key = os.getenv('AWS_ACCESS_KEY_ID')
                secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
                region = os.getenv('AWS_DEFAULT_REGION')
                
                if not re.match(r'^AKIA[0-9A-Z]{16}$', access_key):
                    errors.append("Invalid AWS Access Key ID format")
                
                if len(secret_key) != 40:
                    errors.append("Invalid AWS Secret Access Key format")
                    
                if not re.match(r'^[a-z0-9-]+$', region):
                    errors.append("Invalid AWS region format")
                
                if not errors:
                    logger.info("Valid AWS credentials found")
                    self._log_key_usage("AWS_CREDENTIALS", "validation_success")
        
        # Ensure at least one provider is configured
        if not has_provider:
            errors.append(
                "No AI provider configured. Set at least one of: "
                "OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, or AWS credentials"
            )
        
        # Log validation results
        if errors:
            logger.error("API key validation failed", errors=errors)
            for error in errors:
                self._log_key_usage("VALIDATION", f"error: {error}")
        else:
            logger.info("All API keys validated successfully")
            self._log_key_usage("VALIDATION", "all_keys_valid")
        
        return len(errors) == 0, errors
    
    def check_key_rotation_needed(self) -> Dict[str, bool]:
        """
        Check if any API keys need rotation based on age or usage patterns.
        
        Returns:
            Dict mapping key names to rotation needed status
        """
        rotation_needed = {}
        
        # Check audit log for key age and usage patterns
        audit_data = self._load_audit_log()
        current_time = time.time()
        
        # Rotation policy: warn after 90 days, require after 180 days
        warn_threshold = 90 * 24 * 3600  # 90 days in seconds
        require_threshold = 180 * 24 * 3600  # 180 days in seconds
        
        for key_name in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY', 'AWS_CREDENTIALS']:
            if key_name in audit_data:
                first_use = audit_data[key_name].get('first_use', current_time)
                age = current_time - first_use
                
                if age > require_threshold:
                    rotation_needed[key_name] = True
                    logger.warning(f"API key rotation required for {key_name}", age_days=age/86400)
                elif age > warn_threshold:
                    logger.info(f"API key rotation recommended for {key_name}", age_days=age/86400)
                    rotation_needed[key_name] = False
                else:
                    rotation_needed[key_name] = False
        
        return rotation_needed
    
    def _log_key_usage(self, key_name: str, event: str):
        """Log API key usage for audit purposes."""
        audit_data = self._load_audit_log()
        current_time = time.time()
        
        if key_name not in audit_data:
            audit_data[key_name] = {
                'first_use': current_time,
                'events': []
            }
        
        # Add event to log
        audit_data[key_name]['events'].append({
            'timestamp': current_time,
            'event': event,
            'iso_time': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(current_time))
        })
        
        # Keep only last 1000 events per key
        if len(audit_data[key_name]['events']) > 1000:
            audit_data[key_name]['events'] = audit_data[key_name]['events'][-1000:]
        
        self._save_audit_log(audit_data)
    
    def _load_audit_log(self) -> Dict:
        """Load audit log from disk."""
        try:
            if self.audit_log_path.exists():
                with open(self.audit_log_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning("Failed to load secrets audit log", error=str(e))
        
        return {}
    
    def _save_audit_log(self, data: Dict):
        """Save audit log to disk."""
        try:
            # Ensure directory exists
            self.audit_log_path.parent.mkdir(exist_ok=True)
            
            with open(self.audit_log_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save secrets audit log", error=str(e))
    
    def get_masked_key_info(self) -> Dict[str, str]:
        """
        Get information about configured keys with masked values for logging.
        
        Returns:
            Dict mapping key names to masked values
        """
        info = {}
        
        keys_to_check = [
            'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY',
            'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'
        ]
        
        for key_name in keys_to_check:
            value = os.getenv(key_name)
            if value:
                if len(value) > 8:
                    masked = value[:4] + '*' * (len(value) - 8) + value[-4:]
                else:
                    masked = '*' * len(value)
                info[key_name] = masked
            else:
                info[key_name] = "not_set"
        
        return info


# Global secrets manager instance
secrets_manager = SecretsManager()


def validate_startup_secrets() -> bool:
    """
    Validate secrets on startup and exit if invalid.
    
    Returns:
        True if all secrets are valid, False otherwise
    """
    valid, errors = secrets_manager.validate_api_keys_on_startup()
    
    if not valid:
        logger.error("Startup validation failed", errors=errors)
        print("\n❌ API Key Validation Failed:")
        for error in errors:
            print(f"  • {error}")
        print("\nPlease check your environment variables and try again.")
        return False
    
    logger.info("✅ All API keys validated successfully")
    return True