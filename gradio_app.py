import gradio as gr
from utils import get_openai_verdict_2
import argparse


parser = argparse.ArgumentParser(description='Stock Analysis Tool')
parser.add_argument('--max_tickers', type=int, default=5, help='Maximum number of tickers')
args = parser.parse_args()

max_tickers = args.max_tickers


def variable_inputs(k):

    k = int(k)
    return [gr.Textbox(visible=True)] * k + [gr.Textbox(visible=False)] * (max_tickers - k)

async def analyze_stocks(*args):
    industry_input = args[-1]
    tickers = args[:-1]
    
    tickers = [ticker for ticker in tickers if ticker]
    
    # Process tickers asynchronously
    result = await get_openai_verdict_2(tickers, industry_input)
    
    return result

with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            industry_input = gr.Textbox(label="Industry")
            num_tickers_slider = gr.Slider(1, max_tickers, value=1, step=1, label="Number of Stock Tickers")
            ticker_inputs = []
            for i in range(max_tickers):
                ticker_input = gr.Textbox(label=f"Stock Ticker {i+1}", visible=False)
                ticker_inputs.append(ticker_input)
            num_tickers_slider.change(variable_inputs, num_tickers_slider, ticker_inputs)

        with gr.Column():
            output_text = gr.Textbox(label="OpenAI Analysis")

            concat_btn = gr.Button("Analyze Stocks with OpenAI")
    
    
    
    concat_btn.click(analyze_stocks, inputs=[*ticker_inputs, industry_input], outputs=output_text)


if __name__ == "__main__":
    demo.launch(ssl_verify=False, share=False, debug=False)
