from flask import Flask, jsonify, render_template, request

from .config import AppConfig
from .service import LanguageTutorService


def create_app() -> Flask:
    config = AppConfig.from_env()

    app = Flask(
        __name__,
        static_folder=str(config.static_dir),
        template_folder=str(config.templates_dir),
    )
    app.secret_key = config.secret_key

    tutor_service = LanguageTutorService.from_config(config)

    @app.get("/")
    def serve_index():
        return render_template(
            "index.html",
            language_options=config.language_options,
            level_options=config.level_options,
            ui_text=config.ui_text,
            app_config=config.frontend_config,
        )

    @app.get("/generate_phrase")
    def generate_phrase():
        try:
            phrase = tutor_service.generate_phrase(
                level=request.args.get("level", config.default_level),
                language=request.args.get("language", config.default_language),
                context=(request.args.get("context") or "").strip(),
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except Exception:
            return jsonify({"error": config.ui_text["phrase_generation_error"]}), 502

        return jsonify({"phrase": phrase})

    @app.post("/check_translation")
    def check_translation():
        data = request.get_json(silent=True) or {}
        source_phrase = (data.get("source_phrase") or data.get("german_phrase") or "").strip()
        user_translation = (data.get("user_translation") or "").strip()

        if not source_phrase or not user_translation:
            return jsonify({"error": config.ui_text["invalid_input_error"]}), 400

        try:
            result = tutor_service.check_translation(
                source_phrase=source_phrase,
                user_translation=user_translation,
            )
        except Exception:
            return jsonify({"error": config.ui_text["translation_check_error"]}), 502

        return jsonify(result.to_dict())

    return app


app = create_app()
