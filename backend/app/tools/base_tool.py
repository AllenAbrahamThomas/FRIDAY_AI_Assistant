from abc import ABC, abstractmethod
import time
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    def __init__(self, name: str, description: str, timeout: float = 15.0):
        self.name = name
        self.description = description
        self.timeout = timeout

    @abstractmethod
    async def _run(self, **kwargs) -> Any:
        """Core tool implementation logic."""
        pass

    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Executes the tool with standardized timing, timeout, and exception containment.
        """
        start_time = time.perf_counter()
        try:
            result = await asyncio.wait_for(self._run(**kwargs), timeout=self.timeout)
            duration = round(time.perf_counter() - start_time, 3)
            return {
                "tool_name": self.name,
                "success": True,
                "data": result,
                "error": None,
                "duration_seconds": duration
            }
        except asyncio.TimeoutError:
            duration = round(time.perf_counter() - start_time, 3)
            err_msg = f"Tool '{self.name}' timed out after {self.timeout}s"
            logger.warning(err_msg)
            return {
                "tool_name": self.name,
                "success": False,
                "data": None,
                "error": err_msg,
                "duration_seconds": duration
            }
        except Exception as e:
            duration = round(time.perf_counter() - start_time, 3)
            err_msg = f"Tool '{self.name}' failed: {str(e)}"
            logger.error(err_msg)
            return {
                "tool_name": self.name,
                "success": False,
                "data": None,
                "error": err_msg,
                "duration_seconds": duration
            }
