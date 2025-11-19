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

            if (!sourceWidget || !imageWidget) return;

            const origSourceCallback = sourceWidget.callback;

            sourceWidget.callback = function (value) {
                if (origSourceCallback) {
                    origSourceCallback.apply(this, arguments);
                }

                if (value === "http") {
                    imageWidget.value = null;

                    imageWidget.options = imageWidget.options || {};
                    if ("image" in imageWidget.options) {
                        imageWidget.options.image = null;
                    }
                    if ("preview" in imageWidget.options) {
                        imageWidget.options.preview = null;
                    }

                    if (appInstance?.graph) {
                        appInstance.graph.setDirtyCanvas(true, true);
                    }
                }
            };
        };
    },
});

