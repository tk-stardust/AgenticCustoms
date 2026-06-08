"""Agent 基类——统一定义 run() 接口与输入输出校验协议"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC, Generic[T]):
    """Agent 基类——子类实现 run() 方法，可选覆写 validate_input / validate_output"""

    @abstractmethod
    async def run(self, **kwargs) -> T:
        """执行智能体主逻辑，返回特定领域结果实体"""
        ...

    def validate_input(self, **kwargs) -> None:
        """前置校验——默认不做检查，子类按需覆写"""

    def validate_output(self, result: T) -> bool:
        """后置校验——默认不做检查，子类按需覆写"""
        return True
