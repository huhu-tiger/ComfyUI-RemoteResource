
import os
import sys
import hashlib
import logging
import mimetypes
import shutil
import ssl
from urllib.parse import urlparse
from urllib.request import urlopen

import folder_paths
import node_helpers

import torch
import numpy as np
from PIL import Image, ImageOps, ImageSequence


class LoadImageFromRemoteNode:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = []
        
        # 递归遍历所有子目录
        for root, dirs, filenames in os.walk(input_dir):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                if os.path.isfile(file_path):
                    # 获取相对于 input_dir 的路径
                    rel_path = os.path.relpath(file_path, input_dir)
                    # 统一路径分隔符为 /
                    rel_path = rel_path.replace(os.sep, '/')
                    
                    # 如果是根目录下的文件，只使用文件名（保持原有逻辑）
                    # 如果是子目录下的文件，使用相对路径
                    if os.path.dirname(rel_path) == '':
                        # 根目录下的文件，只使用文件名
                        files.append(filename)
                    else:
                        # 子目录下的文件，使用相对路径
                        files.append(rel_path)
        
        # logging.info(f"[LoadImageFromRemote] 扫描到的所有文件 ({len(files)} 个): {files}")
        # 筛选出图像文件
        files = folder_paths.filter_files_content_types(files, ["image"])
        # logging.info(f"[LoadImageFromRemote] 筛选后的图像文件 ({len(files)} 个): {files}")
        image_options = sorted(files) if files else []
        # 为了让本地模式正常显示预览，这里将 image 放在 required 中（和原生 LoadImage 一致）
        # 实际上在 HTTP 模式下并不会校验 image，因此运行时并不是“必填”
        return {
            "required": {
                "source": (["local", "http"], {"default": "local"}),
                "image": (image_options, {"image_upload": True}),
            },
            "optional": {
                "http_url": ("STRING", {"default": "", "multiline": False}),
            },
        }

    CATEGORY = "image"

    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "load_image"
    def load_image(self, source, image=None, http_url=""):
        if source == "http":
            # HTTP 模式下忽略 image 参数，使用 http_url
            image_path = self._download_http_image(http_url)
            logging.info(f"[LoadImageFromRemote] 下载完成: {http_url} -> {image_path}")
        else:
            # Local 模式下使用 image 参数
            if not image or image == "":
                raise ValueError("请选择本地图片或切换到 HTTP 模式。")
            image_path = folder_paths.get_annotated_filepath(image)

        return self._load_from_path(image_path)

    def _load_from_path(self, image_path):
        img = node_helpers.pillow(Image.open, image_path)

        output_images = []
        output_masks = []
        w, h = None, None

        excluded_formats = ['MPO']

        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)

            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]

            if image.size[0] != w or image.size[1] != h:
                continue

            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            elif i.mode == 'P' and 'transparency' in i.info:
                mask = np.array(i.convert('RGBA').getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))

        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]

        return (output_image, output_mask)

    def _download_http_image(self, url):
        if not url or not url.lower().startswith(("http://", "https://")):
            raise ValueError("HTTP 模式需要以 http/https 开头的 URL。")

        temp_dir = os.path.join(folder_paths.get_temp_directory(), "remote_downloads")
        os.makedirs(temp_dir, exist_ok=True)

        parsed = urlparse(url)
        url_path = parsed.path.rstrip("/")
        original_name = os.path.basename(url_path) if url_path else "remote_image"

        _, ext = os.path.splitext(original_name)

        try:
            # HTTP(S) 下载时跳过证书验证，避免自签名/不匹配证书导致失败
            context = ssl._create_unverified_context()
            with urlopen(url, context=context) as response:
                content_type = response.headers.get("Content-Type", "")
                if not ext:
                    guessed_ext = mimetypes.guess_extension(content_type.partition(";")[0].strip()) if content_type else ""
                    if guessed_ext:
                        ext = guessed_ext
                if not ext:
                    ext = ".img"

                hashed_name = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
                filename = f"{hashed_name}_{original_name or 'image'}"
                if not filename.endswith(ext):
                    filename = f"{filename}{ext}"

                temp_path = os.path.join(temp_dir, filename)

                with open(temp_path, "wb") as f:
                    shutil.copyfileobj(response, f)

            logging.info(f"[LoadImageFromRemote] 下载完成: {url} -> {temp_path}")
            return temp_path
        except Exception as exc:
            logging.error(f"[LoadImageFromRemote] 下载失败: {url}, {exc}")
            raise

    @classmethod
    def IS_CHANGED(s, source, image=None, http_url=""):
        if source == "http":
            # HTTP 模式下基于 URL 的哈希值
            return hashlib.sha256(http_url.encode("utf-8")).hexdigest()

        # Local 模式下基于文件内容的哈希值
        if not image or image == "":
            return hashlib.sha256("missing_local_image".encode("utf-8")).hexdigest()
        
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(s, source, image=None, http_url=""):
        if source == "http":
            # HTTP 模式下验证 URL，image 可以为空字符串（前端会自动清空预览）
            if not http_url or not http_url.lower().startswith(("http://", "https://")):
                return "HTTP 模式需要以 http/https 开头的链接"
            # 在 HTTP 模式下，允许 image 为空，前端会清空预览
            return True

        # Local 模式下验证图片文件
        if not image or image == "":
            return "请选择本地图片。"
        
        if not folder_paths.exists_annotated_filepath(image):
            return "Invalid image file: {}".format(image)

        return True