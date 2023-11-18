# -*- coding: utf-8 -*-
# @Time    : 2023/11/18 上午1:10
# @Author  : sudoskys
# @File    : schema.py
# @Software: PyCharm
from typing import Tuple, List

from pydantic import BaseModel


class NaiResult(BaseModel):
    class RequestParams(BaseModel):
        endpoint: str
        raw_request: dict = None

    meta: RequestParams
    files: List[Tuple[str, bytes]] = None

    def query_params(self, key: str, default=None):
        return self.meta.raw_request.get(key, default)
