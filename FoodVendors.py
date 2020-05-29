from flask import Flask, request, jsonify

app = Flask(__name__)

VENDOR_INVENTORY = {
    "Store A": {
        "flour": {
            "count": 3,
            "price": "$4.99"
        },
        "eggs": {
            "count": 5,
            "price": "$3.99"
        },
        "milk": {
            "count": 3,
            "price": "$2.99"
        }
    },

    "Store B": {
        "flour": {
            "count": 6,
            "price": "$3.99"
        },
        "eggs": {
            "count": 8,
            "price": "$4.99"
        },
        "milk": {
            "count": 4,
            "price": "$3.99"
        }
    },

    "Store C": {
        "flour": {
            "count": 2,
            "price": "$5.99"
        },
        "yeast": {
            "count": 4,
            "price": "$8.99"
        }
    },

    "Store D": {
        "flour": {
            "count": 3,
            "price": "$3.99"
        },
        "milk": {
            "count": 5,
            "price": "$3.99"
        }
    }
}

@app.route('/')
def serve():
    store = request.args.get('vendor')
    food_product = request.args.get('item')
    return jsonify(data = VENDOR_INVENTORY[store][food_product.lower()])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
