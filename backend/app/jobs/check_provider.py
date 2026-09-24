"""Read the public model catalog; never spends tokens or tests paid inference."""

import httpx

from app.core.config import settings

if __name__ == "__main__":
    config = settings()
    response = httpx.get(config.openrouter_base_url.rstrip("/") + "/models", timeout=20)
    response.raise_for_status()
    supported = [
        model
        for model in response.json()["data"]
        if model["id"].startswith("qwen/")
        and {"structured_outputs", "response_format"}.issubset(model.get("supported_parameters", []))
    ]
    if config.openrouter_model:
        if not any(m["id"] == config.openrouter_model for m in supported):
            raise SystemExit(
                "Configured Qwen model is not advertised with both required parameters; select another endpoint."
            )
        print(
            "Configured model appears in the structured-output catalog. This is not a paid model-call validation."
        )
    else:
        print("Set OPENROUTER_MODEL to a currently supported Qwen ID. Examples from this live catalog:")
        print("\n".join(m["id"] for m in supported[:12]))
