# Components, model terms and attribution

GesturePortal combines components with different terms. A single blanket project license has not been selected for the original project code. Public availability alone does not grant an unrestricted license to every file. Retained third-party notices apply to their respective components, and downloaded weights have their own terms.

| Component | Source | Terms / retained notice |
| --- | --- | --- |
| AnimeGANv2 PyTorch implementation | [bryandlee/animegan2-pytorch](https://github.com/bryandlee/animegan2-pytorch) | [MIT notice](../custom_nodes/gesture_portal/animegan2/LICENSE); consult upstream for the supplied face-paint weights |
| Portrait face mask/alignment reference | [menyifang/DCT-Net](https://github.com/menyifang/DCT-Net), [ModelScope assets](https://modelscope.cn/models/iic/cv_unet_person-image-cartoon_compound-models) | [Apache-2.0 notice](../custom_nodes/gesture_portal/dctnet_LICENSE) |
| YuNet face detector | [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) | [MIT notice](licenses/yunet-LICENSE) |
| FLUX.2 Klein 4B | [Black Forest Labs](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B), [Comfy-packaged files](https://huggingface.co/Comfy-Org/flux2-klein-4B) | Apache-2.0 model release; consult model/encoder component cards |
| Qwen Image 2.1 | [Qwen model card](https://huggingface.co/Qwen/Qwen-Image-2.1) | [Qwen research license](../custom_nodes/gesture_portal/qwen_research_LICENSE) |
| Qwen Image 2.1 Viggle Turbo v0.3 | [Viggle model card](https://huggingface.co/Viggle/Qwen-Image-2.1-viggle-turbo) | Same research terms; [retained NOTICE](../custom_nodes/gesture_portal/qwen_research_NOTICE) |

**Built with Qwen.** The resolution-shifted Turbo scheduling helper in `custom_nodes/gesture_portal/editing.py` is adapted from Viggle's published ComfyUI implementation; its source revision is identified in that module. The NOTICE describes the upstream derivative and its files; this repository does not distribute those model weights.

Qwen support is intended for this project's non-commercial research and evaluation purpose. Setup requires an explicit `-QwenResearch` option. Review the full license for the precise permissions, obligations and restrictions rather than treating it as Apache/MIT or as unrestricted commercial permission.

ComfyUI, MediaPipe, OpenCV, NumPy, Requests, PyTorch and their dependencies retain their respective upstream licenses. This repository integrates existing models; it does not claim authorship of their training or weights, or endorsement by their authors.

The public demo media was supplied by the project creator. Promo/interface artwork was created separately using the built-in image-generation tool. These visual assets are not new runtime model outputs. No separate blanket media license has been assigned.
