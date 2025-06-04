from flask import Flask, jsonify, render_template
from topo_cam6 import run, ping_all, run_iperf_tcp as run_iperf
import subprocess

app = Flask(__name__, template_folder='../frontend/templates')

net = None  # Store running network instance


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start_network():
    global net
    try:
        net = run()
        return jsonify({"status": "success", "message": "Network started"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/stop", methods=["POST"])
def stop_network():
    global net
    if net:
        net.stop()
        net = None
        return jsonify({"status": "success", "message": "Network stopped"})
    return jsonify({"status": "error", "message": "Network is not running"}), 400


@app.route("/pingall", methods=["GET"])
def ping_all_route():
    if net:
        result = ping_all(net)
        return jsonify({"status": "success", "output": result})
    return jsonify({"status": "error", "message": "Network not started"}), 400


@app.route("/iperf", methods=["GET"])
def iperf_route():
    if net:
        run_iperf(net)
        return jsonify({"status": "success", "message": "iPerf completed (see logs)."})
    return jsonify({"status": "error", "message": "Network not started"}), 400


@app.route("/inject_flows", methods=["POST"])
def inject_flows():
    try:
        import flow_rule
        success = flow_rule.inject_flow_rules()
        if success:
            return jsonify({"status": "success", "message": "Flow rules injected successfully"})
        else:
            return jsonify({"status": "error", "message": "Failed to inject some flow rules"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)