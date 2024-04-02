# gpt-investor

This is a fork of [gpt investor](https://github.com/mshumer/gpt-investor) .

The code uses OpenAI API instead of Claude, replaces synchronous API calls with asynchronous ones, and adds a Gradio UI.

To use the Gradio UI, follow these steps:

```
conda create --name gptinvestor python=3.10
conda activate gptinvestor
pip install -r requirements.txt
```

And then run the Gradio UI:
```
python gradio_app.py --max_tickers 5
```
