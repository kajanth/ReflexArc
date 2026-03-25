import sys
from unittest.mock import MagicMock
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.web'] = MagicMock()

import pytest
sys.exit(pytest.main(["-p", "no:asyncio", "tests/integration/test_security_features.py"]))
