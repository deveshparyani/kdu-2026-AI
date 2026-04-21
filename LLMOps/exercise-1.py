from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM
import torch

def main():
    model_name = "distilgpt2"
    input_text = "Transformers are powerful because"

    print(f"Loading model: {model_name}")

    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Some GPT-style models do not have a pad token by default
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Base model (for hidden states / embeddings)
    base_model = AutoModel.from_pretrained(model_name)

    # Causal LM model (for text generation)
    gen_model = AutoModelForCausalLM.from_pretrained(model_name)

    base_model.eval()
    gen_model.eval()

    print("\n--- Tokenization Flow ---")
    print("Original text:")
    print(input_text)

    tokens = tokenizer.tokenize(input_text)
    token_ids = tokenizer.convert_tokens_to_ids(tokens)
    encoded = tokenizer(input_text, return_tensors="pt")

    print("\nTokens:")
    print(tokens)

    print("\nToken IDs:")
    print(token_ids)

    print("\nEncoded tensor:")
    print(encoded["input_ids"])

    print("\n--- Basic Inference with AutoModel ---")
    with torch.no_grad():
        outputs = base_model(**encoded)

    last_hidden_state = outputs.last_hidden_state
    print("Last hidden state shape:", last_hidden_state.shape)
    # shape = [batch_size, sequence_length, hidden_size]

    print("\n--- Text Generation with AutoModelForCausalLM ---")

    generation_settings = [
        {
            "name": "Setting 1: low temperature, focused output",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_new_tokens": 30
        },
        {
            "name": "Setting 2: higher temperature, more creative",
            "temperature": 1.1,
            "top_p": 0.95,
            "max_new_tokens": 30
        },
        {
            "name": "Setting 3: longer output",
            "temperature": 0.8,
            "top_p": 0.92,
            "max_new_tokens": 60
        }
    ]

    for setting in generation_settings:
        print(f"\n{setting['name']}")
        print(
            f"temperature={setting['temperature']}, "
            f"top_p={setting['top_p']}, "
            f"max_new_tokens={setting['max_new_tokens']}"
        )

        with torch.no_grad():
            generated_ids = gen_model.generate(
                **encoded,
                do_sample=True,
                temperature=setting["temperature"],
                top_p=setting["top_p"],
                max_new_tokens=setting["max_new_tokens"],
                pad_token_id=tokenizer.eos_token_id
            )

        generated_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        print("Generated text:")
        print(generated_text)


if __name__ == "__main__":
    main()