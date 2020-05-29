from flask import Flask, request, jsonify

app = Flask(__name__)

# Products listed are mapped to an array of stores that carry
# the product. The number associated with each store represents
# how many of the respective product the store has in stock.
# A store that has a stock of 0 still carries the product, but
# the product is temporarily out of stock.

PRODUCT_LIST = {
    "flour": [
            "Store A",
            "Store B",
            "Store C",
            "Store D"
    ],

    "eggs": [
            "Store A",
            "Store B"
    ],

    "yeast": [
            "Store C",
    ],

    "milk": [
            "Store A",
            "Store B",
            "Store D"
    ],

    "yogurt": []
}

def initialize_tracer():
    exporter = StackdriverExporter()
    tracer = Tracer(
        exporter=exporter,
        sampler=AlwaysOnSampler()
    )
    return tracer

@app.route('/')
def serve():
    food_search_query = request.args.get('food_product')

    if not food_search_query:
        return jsonify(data = []), 400

    if not food_search_query.lower() in PRODUCT_LIST:
        return jsonify(data = []), 404

    return jsonify(data = PRODUCT_LIST[food_search_query.lower()]), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
