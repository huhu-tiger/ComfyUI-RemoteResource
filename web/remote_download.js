import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Comfy.RemoteDownload.ClearLocalPreviewOnHttp",

    async beforeRegisterNodeDef(nodeType, nodeData, appInstance) {
        const supportedNames = ["LoadImageFromRemote", "LoadImageFromRemoteNode"];
        if (!nodeData || !supportedNames.includes(nodeData.name)) return;

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            if (origOnNodeCreated) {
                origOnNodeCreated.apply(this, arguments);
            }

            const node = this;
            if (!node.widgets || !Array.isArray(node.widgets)) return;

            const sourceWidget = node.widgets.find((w) => w.name === "source");
            const imageWidget = node.widgets.find((w) => w.name === "image");
            const httpUrlWidget = node.widgets.find((w) => w.name === "http_url");

            if (!sourceWidget || !imageWidget) return;

            const origSourceCallback = sourceWidget.callback;

            // 更新 widget 状态的函数
            const updateWidgetsVisibility = (sourceValue) => {
                if (sourceValue === "http") {
                    // HTTP 模式：清空 image widget 的预览
                    imageWidget.value = null;
                    imageWidget.options = imageWidget.options || {};
                    if ("image" in imageWidget.options) {
                        imageWidget.options.image = null;
                    }
                    if ("preview" in imageWidget.options) {
                        imageWidget.options.preview = null;
                    }
                    
                    // 确保 http_url widget 存在且可用
                    if (httpUrlWidget) {
                        // 如果 http_url 为空，设置为空字符串以确保 widget 可见
                        if (httpUrlWidget.value === undefined || httpUrlWidget.value === null) {
                            httpUrlWidget.value = "";
                        }
                    }
                } else {
                    // Local 模式：清空 http_url（可选）
                    if (httpUrlWidget) {
                        httpUrlWidget.value = "";
                    }
                }
                
                // 强制更新节点显示和大小
                if (appInstance?.graph) {
                    appInstance.graph.setDirtyCanvas(true, true);
                }
                
                // 触发节点重新计算大小和布局
                if (node.setSize) {
                    node.setSize(node.computeSize());
                } else if (node.onResize) {
                    node.onResize();
                }
            };

            // 初始化时应用当前状态
            if (sourceWidget.value) {
                // 使用 setTimeout 确保节点完全初始化后再更新
                setTimeout(() => {
                    updateWidgetsVisibility(sourceWidget.value);
                }, 0);
            }

            sourceWidget.callback = function (value) {
                if (origSourceCallback) {
                    origSourceCallback.apply(this, arguments);
                }

                updateWidgetsVisibility(value);
            };
        };
    },
});

