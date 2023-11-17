# -*- coding: utf-8 -*-
# @Time    : 2023/11/18 上午1:56
# @Author  : sudoskys
# @File    : command.py
# @Software: PyCharm

from arclet.alconna import Alconna, Args, Option, CommandMeta

from app.core import NovelAiInference

DrawCommand = Alconna(
    "/draw",
    Args['prompt', str],
    Option("--negative_prompt|-neg", Args.negative_prompt[str], help_text="设置负面提示"),
    Option("--seed|-s", Args['seed', int], help_text="设置随机种子"),
    # Option("--steps|-st", Args['steps', Annotated[int, lambda x: x < 50]], help_text="设置步数"),
    Option("--cfg_rescale|-cfg", Args['cfg_rescale', int], help_text="设置cfg_rescale"),
    Option("--sampler|-sam", Args["sampler", NovelAiInference.valid_sampler()], help_text="设置采样方式"),
    Option("--width|-wi", Args['width', int], help_text="设置宽度"),
    Option("--height|-he", Args['height', int], help_text="设置高度"),
    meta=CommandMeta(fuzzy_match=True,
                     usage="draw [prompt] [-neg negative_prompt] [-s seed] "
                           "[-cfg cfg_rescale] [-sam sampler] [-w width] [-h height]",
                     description="使用指定的prompt生成图片"
                     )
)

if __name__ == "__main__":
    sm = DrawCommand.parse(
        "/draw --negative_prompt 负面提示 --seed 123 --cfg_rescale 123 --sampler k_dpmpp_2m --width 123 --height 123 123"
    )
    print(DrawCommand.get_help())
    print(sm)
    print(sm.all_matched_args)
    dov = DrawCommand.parse("/draw aaaaa -nefg aaaa -s 123 -st 123 -cfg 123 -sam k_dpmpp_2m -wi 123 -he 123")
    print(dov)
    print(dov.error_info)
