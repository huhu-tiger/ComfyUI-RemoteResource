from .nodes import LoadImageFromRemoteNode

# 节点名字和Python类的映射
NODE_CLASS_MAPPINGS = {
    "LoadImageFromRemote": LoadImageFromRemoteNode
}

# 节点的显示名字
NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptSelector": "LoadImageFromRemote"
}

# WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]