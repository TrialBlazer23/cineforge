# AI Filmmaking on Google Cloud

This project is an implementation of the "From Story to Screen" blueprint, creating a generative filmmaking pipeline on Google Cloud. It transforms a written story into a finished film by orchestrating Google's generative AI models (Gemini, Imagen, Veo) through a series of automated steps.

## Pipeline Stages

1.  **Narrative Deconstruction**: Analyzes a raw text story to produce a structured "Narrative Schema" in JSON format.
2.  **Screenplay & Storyboard Generation**: Generates a screenplay and a descriptive text-based storyboard from the Narrative Schema.
3.  **Visual Asset Generation**: Creates character model sheets, environment plates, and consistent storyboard images using Imagen.
4.  **Video Synthesis**: Animates the storyboard images into video clips using Veo.
5.  **Final Assembly**: Assembles the video clips into a final film using FFmpeg.

This application is designed with a "human-in-the-loop" workflow, allowing for review and approval at each critical stage of the creative process.
