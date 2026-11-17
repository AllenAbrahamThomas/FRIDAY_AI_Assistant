from abc import ABC, abstractmethod
import time
import asyncio
import logging
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, ConfigDict, ValidationError

logger = logging.getLogger(__name__)

class EmptyToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

class BaseTool(ABC):
    def __init__(
        self,
        name: str,
        description: str,
        timeout: float = 15.0,
        input_model: Type[BaseModel] = EmptyToolInput,
        output_schema: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.description = description
        self.timeout = timeout
        self.input_model = input_model
        self.input_schema = input_model.model_json_schema()
        self.output_schema = output_schema or {"description": "Tool output"}

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
            validated_input = self.input_model.model_validate(kwargs)
            result = await asyncio.wait_for(
                self._run(**validated_input.model_dump()),
                timeout=self.timeout
            )
            duration = round(time.perf_counter() - start_time, 3)
            return {
                "tool_name": self.name,
                "success": True,
                "data": result,
                "error": None,
                "duration_seconds": duration
            }
        except ValidationError as exc:
            duration = round(time.perf_counter() - start_time, 3)
            details = "; ".join(
                f"{'.'.join(str(part) for part in error['loc']) or 'input'}: {error['msg']}"
                for error in exc.errors()
            )
            error_message = f"Invalid input for tool '{self.name}': {details}"
            logger.warning(error_message)
            return {
                "tool_name": self.name,
                "success": False,
                "data": None,
                "error": error_message,
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
