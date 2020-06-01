import logging
import os
import requests
import json
import time

from opencensus.ext.stackdriver.trace_exporter import StackdriverExporter
from opencensus.ext.stackdriver import stats_exporter
from opencensus.trace.tracer import Tracer
from opencensus.trace.samplers import AlwaysOnSampler
from opencensus.stats import aggregation
from opencensus.stats import measure
from opencensus.stats import stats
from opencensus.stats import view

from threading import Thread
from flask import Flask, request

app = Flask(__name__)

FOOD_SUPPLIER_ADDRESS = "http://34.86.204.38:5000"
FOOD_VENDOR_ADDRESS = "http://34.86.232.249:5000"

SUBMISSION_FORM = """
                	<form method="GET" action="/search-vendors" enctype="multipart/form-data">
                        	<input type="text" name="food_product">
                        	<input type="submit">
              		</form>
        	  """

LATENCY_MEASURE = measure.MeasureFloat(
	"request_latency",
	"The request latency in ms",
	"ms"
)

RPC_MEASURE = measure.MeasureInt(
	"rpc_count",
	"The number of RPCs",
	"1"
)

FLOAT_AGGREGATION_DISTRIBUTION = aggregation.DistributionAggregation(
	[1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0]
)

INT_AGGREGATION_DISTRIBUTION = aggregation.DistributionAggregation(
	[1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
)

FOOD_SERVICE_LATENCY_VIEW = view.View(
	"foodservice_request_latency_distribution",
	"The distribution of the request latencies for FoodService calls",
	[],
	LATENCY_MEASURE,
	FLOAT_AGGREGATION_DISTRIBUTION
)

FOOD_VENDOR_LATENCY_VIEW = view.View(
	"foodvendor_request_latency_distribution",
	"The distribution of the request latencies for FoodVendor calls",
	[],
	LATENCY_MEASURE,
	FLOAT_AGGREGATION_DISTRIBUTION
)

RPC_COUNT_VIEW = view.View(
	"rpc_count_distribution",
	"The distribution of rpcs made per FoodFinder request",
	[],
	RPC_MEASURE,
	INT_AGGREGATION_DISTRIBUTION
)

RPC_ERROR_VIEW = view.View(
	"rpc_error_diestribution",
	"The distributione of rpc errors made per FoodFinder request",
	[],
	RPC_MEASURE,
	INT_AGGREGATION_DISTRIBUTION
)

def initialize_tracer():
	exporter = StackdriverExporter()
	tracer = Tracer(
		exporter=exporter,
		sampler=AlwaysOnSampler()
	)
	return tracer

def register_views(view_manager):
	view_manager.register_view(FOOD_SERVICE_LATENCY_VIEW)
	view_manager.register_view(FOOD_VENDOR_LATENCY_VIEW)
	view_manager.register_view(RPC_COUNT_VIEW)
	view_manager.register_view(RPC_ERROR_VIEW)

def make_vendor_request(vendor, food_item, response_list, index):
	tracer = app.config['TRACER']
	monitor = app.config['STATS']
	
	start = time.time()
	tracer.span(name='FoodVendor')
	try:
		response_list[index] = json.loads(requests.get(FOOD_VENDOR_ADDRESS, params = { 'vendor': vendor, 'item': food_item }).text)['data']
	except:
		app.config['ERRORS'] += 1
	
	tracer.end_span()
	end = (time.time() - start) * 1000.0
	monitor.measure_float_put(LATENCY_MEASURE, end)
	monitor.record()	

def process_vendor_list(vendor_list, food_item):
	threads = [None] * len(vendor_list)
	responses = [None] * len(vendor_list)

	for index in range(len(threads)):
		threads[index] = Thread(target=make_vendor_request, args=(vendor_list[index], food_item, responses, index))
		threads[index].start()

	for index in range(len(threads)):
		threads[index].join()

	return responses

@app.route('/')
def index():
	return SUBMISSION_FORM

@app.route('/search-vendors', methods=['GET'])
def search_vendors():
	tracer = app.config['TRACER']
	monitor = app.config['STATS']
	app.config['ERRORS'] = 0
	app.config['NUM_RPCS']

	vendor_response = None

	with tracer.span(name='FoodFinder') as food_finder_span:
		food_search_query = request.args.get('food_product')
		food_finder_span.add_annotation(food_search_query + " searched")

		vendor_search_response = None
		with tracer.span(name='FoodService') as food_service_span:
			try:
				vendor_search_response = requests.get(FOOD_SUPPLIER_ADDRESS, params = { 'food_product': food_search_query })
			except:
				app.config['ERRORS'] += 1
			finally:
				app.config['NUM_RPCS'] += 1

		vendor_list = json.loads(vendor_search_response.text)['data']

		food_finder_span.add_annotation(str(len(vendor_list)) + " vendors found with FoodService")

		if len(vendor_list) == 0:
			monitor.measure_int_put(RPC_MEASURE, app.config['NUM_RPCS'])
			monitor.record()

			if app.config['ERRORS'] > 0:
				monitor.measure_input_put(RPC_MEASURE, app.config['ERRORS'])
				monitor.record()

			if vendor_search_response.status_code == 400:
				return SUBMISSION_FORM + "<h1>No query submitted.</h1>"
			return SUBMISSION_FORM + "<h1>" + food_search_query + " was not found in the list of food items.</h1>"
	
		response_list = process_vendor_list(vendor_list, food_search_query)
		app.config['NUM_RPCS'] += len(vendor_list)

		vendor_response = SUBMISSION_FORM + "<h1>Results for " + food_search_query + "</h1><table style=\"border-spacing: 1em .5em; padding: 0 2em 1em 0;\"><tr><th>Vendor</th><th>Count</th><th>Price (in USD)</th></tr>"
		for index in range(len(response_list)):
			if (response_list[index] is not None):
				vendor_response += "<tr><td>" + vendor_list[index] + "</td><td>" + str(response_list[index]['count']) + "</td><td>" + response_list[index]['price'] + "</tr>"
			else:
				vendor_response += "<tr><td>This vendor timed out.</td></tr>"

		vendor_response += "</table>"

	monitor.measure_int_put(RPC_MEASURE, app.config['NUM_RPCS'])
	monitor.record()

	if (app.config['ERRORS'] > 0):
		monitor.measure_int_put(RPC_MEASURE, app.config['ERRORS'])
		monitor.record()

	return vendor_response

if __name__ == '__main__':
	tracer = initialize_tracer()
	app.config['TRACER'] = tracer
	app.config['STATS'] = stats.stats.stats_recorder.new_measurement_map()
	app.config['ERRORS'] = 0
	app.config['NUM_RPCS'] = 0
	
	register_views(stats.stats.view_manager)
	
	exporter = stats_exporter.new_stats_exporter()
	stats.stats.view_manager.register_exporter(exporter)

	app.run(host='0.0.0.0', port=5000, debug=True)
