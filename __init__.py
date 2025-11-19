from .nodes import LoadImageFromRemoteNode

# 节点名字和Python类的映射
NODE_CLASS_MAPPINGS = {
    "LoadImageFromRemote": LoadImageFromRemoteNode
}

# 节点的显示名字
NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageFromRemote": "LoadImageFromRemote",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]