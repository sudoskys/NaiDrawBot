# -*- coding: utf-8 -*-
# @Time    : 2023/11/18 上午12:18
# @Author  : sudoskys
# @File    : __init__.py.py
# @Software: PyCharm
import os
from io import BytesIO
from typing import Optional
from zipfile import ZipFile

import httpx
import shortuuid
from PIL import Image
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel, ConfigDict, model_validator, PrivateAttr

from .error import ServerError
from .schema import NaiResult

load_dotenv()


class CheckError(Exception):
    pass


class NovelAiInference(BaseModel):
    _endpoint: Optional[str] = PrivateAttr("https://api.novelai.net")
    _access_token: Optional[str] = PrivateAttr(None)
    _request_timeout: Optional[float] = PrivateAttr(None)

    class Params(BaseModel):
        width: Optional[int] = 832
        height: Optional[int] = 1216
        scale: Optional[int] = 5
        sampler: Optional[str] = "k_euler"
        steps: Optional[int] = 28
        n_samples: Optional[int] = 1
        ucPreset: Optional[int] = 0
        add_original_image: Optional[bool] = False
        cfg_rescale: Optional[int] = 0
        controlnet_strength: Optional[int] = 1
        dynamic_thresholding: Optional[bool] = False
        legacy: Optional[bool] = False
        negative_prompt: Optional[str] = (
            "nsfw, lowres, {bad}, error, fewer, extra, missing, worst quality, "
            "jpeg artifacts, bad quality, watermark, unfinished, displeasing, chromatic aberration, signature,"
            " extra digits, artistic error, username, scan, [abstract]"
        )
        noise_schedule: Optional[str] = "native"
        qualityToggle: Optional[bool] = True
        seed: Optional[int] = 0
        sm: Optional[bool] = False
        sm_dyn: Optional[bool] = False
        uncond_scale: Optional[int] = 1

    action: Optional[str] = "generate"
    input: str = "1girl, best quality, amazing quality, very aesthetic, absurdres"
    model: Optional[str] = "nai-diffusion-3"
    parameters: Params = Params()
    model_config = ConfigDict(extra="ignore")

    @property
    def base_url(self):
        return f"{self.endpoint.strip('/')}/ai/generate-image"

    @property
    def request_timeout(self):
        return self._request_timeout

    @property
    def access_token(self):
        return self._access_token

    @access_token.setter
    def access_token(self, value):
        self._access_token = value

    @property
    def endpoint(self):
        return self._endpoint

    @endpoint.setter
    def endpoint(self, value):
        self._endpoint = value

    @staticmethod
    def valid_sampler():
        return ["k_euler", "k_euler_ancestral", "k_dpmpp_2m", "k_dpmpp_sde", "ddim_v3"]

    @staticmethod
    def valid_wh():
        """
        宽高
        :return:
        """
        return [
            (832, 1216),
            (1216, 832),
            (1024, 1024),
        ]

    @model_validator(mode="after")
    def validate_param(self):
        if self.parameters.steps != 28:
            raise CheckError("steps must be 28.")
        if (self.parameters.width, self.parameters.height) not in self.valid_wh():
            raise CheckError("Invalid size, must be one of 832x1216, 1216x832, 1024x1024")
        if self.parameters.n_samples != 1:
            raise CheckError("n_samples must be 1.")
        if self.parameters.sampler is None:
            self.parameters.sampler = "k_euler"
        if self.parameters.sampler not in self.valid_sampler():
            raise CheckError("Invalid sampler.")
        if self.access_token is None and os.environ.get("NOVEL_AI_TOKEN"):
            self.access_token = os.environ.get("NOVEL_AI_TOKEN")
        else:
            raise CheckError(".env `NOVEL_AI_TOKEN` is required.")
        if os.environ.get("NOVEL_AI_ENDPOINT"):
            self.endpoint = os.environ.get("NOVEL_AI_ENDPOINT")
        return self

    def rebuild(self) -> "NovelAiInference":
        return NovelAiInference(**self.model_dump())

    def update_params(self, **kwargs) -> "NovelAiInference":
        return NovelAiInference(**self.model_dump(), **kwargs)

    @classmethod
    def build(cls, *,
              prompt: str,
              negative_prompt: Optional[str] = None,
              seed: Optional[int] = None,
              steps: Optional[int] = None,
              cfg_rescale: Optional[int] = None,
              sampler: Optional[str] = "k_dpmpp_2m",
              width: Optional[int] = 832,
              height: Optional[int] = 1216,
              ):
        """
        正负面, step, cfg, 采样方式, seed
        :param prompt:
        :param negative_prompt:
        :param seed:
        :param steps:
        :param cfg_rescale:
        :param sampler:
        :param width:
        :param height:
        :return: self
        """
        param = {
            "negative_prompt": negative_prompt,
            "seed": seed,
            "steps": steps,
            "cfg_rescale": cfg_rescale,
            "sampler": sampler,
            "width": width,
            "height": height,
        }
        # 清理空值
        param = {k: v for k, v in param.items() if v is not None}
        return cls(
            input=prompt,
            parameters=cls.Params(**param)
        )

    async def __call__(self) -> NaiResult:
        request_data = self.model_dump()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Origin": "https://novelai.net",
            "Referer": "https://novelai.net/"
        }
        try:
            async with httpx.AsyncClient(timeout=self.request_timeout or 30.0) as client:
                response = await client.post(
                    self.base_url,
                    json=request_data,
                    headers=headers,
                    timeout=self.request_timeout or 30.0,
                )
                logger.info(f"request_data: {request_data}")
                if response.headers.get('Content-Type') != 'application/x-zip-compressed':
                    logger.error(f"response: {response.text}")
                    try:
                        message = response.json()["message"]
                    except Exception:
                        raise ServerError(msg=f"Unexpected content type: {response.headers.get('Content-Type')}")
                    else:
                        raise ServerError(msg=f"[Nai Server]{message}")
                response.raise_for_status()
                zip_file = ZipFile(BytesIO(response.content))
                _return_contents = []
                with zip_file as zf:
                    file_list = zf.namelist()
                    if not file_list:
                        raise ServerError(msg=f"Returned zip file is empty.")
                    with zf.open(file_list[0]) as file:
                        img_file = Image.open(BytesIO(file.read()), "r", formats=["PNG"])
                        # Create a BytesIO object to store the PNG image
                        png_bytes = BytesIO()
                        img_file.save(png_bytes, format="PNG")
                        png_bytes.seek(0)
                        _return_contents.append(
                            (f"{str(shortuuid.uuid()[:5])}.png", png_bytes.getvalue())
                        )
                return NaiResult(
                    meta=NaiResult.RequestParams(
                        endpoint=self.base_url,
                        raw_request=request_data,
                    ),
                    files=_return_contents
                )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"An HTTP error occurred: {exc}")
        except ServerError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"An error occurred: {e}")
