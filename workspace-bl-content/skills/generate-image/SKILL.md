# Skill: generate-image

Generate images for backlink posts when the target site accepts images.

**NEVER use the `image_generate` tool.** Always run this script via `exec`.

```bash
mkdir -p "$RUN_DIR/content/images" && bash ~/.openclaw-backlink/workspace-bl-content/skills/generate-image/generate.sh "<PROMPT>" "$RUN_DIR/content/images/site-domain.jpg"
```

Uses **Vertex Gemini Flash Lite Image** via Bifrost (`http://192.168.32.1:8888/v1`), with **HF FLUX.1 Schnell** fallback.

| Variable | Default |
|----------|---------|
| `IMAGE_MODEL` | `vertex/gemini-3.1-flash-lite-image` |
| `IMAGE_MODEL_FALLBACK` | `huggingface/hf-inference/black-forest-labs/FLUX.1-schnell` |

On success: read path from stdout or `/tmp/image-result.txt`.

On failure: `IMAGE_FAILED: $(cat /tmp/image-error.log)` — set `image_path` null for that site and continue.
