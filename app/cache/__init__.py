# -*- coding: utf-8 -*-
# @Time    : 2023/11/18 上午12:38
# @Author  : sudoskys
# @File    : __init__.py.py
# @Software: PyCharm
from .elara import ElaraClientSyncWrapper

cache = ElaraClientSyncWrapper(backend="elara.db")
