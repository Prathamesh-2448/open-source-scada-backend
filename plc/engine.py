import time
from collections import defaultdict, deque
import operator

# --- GPIO Abstraction Layer ---
class GPIOManager:
    """
    Abstracts actual Raspberry Pi GPIO calls.
    Replace these stubs with actual RPi.GPIO or gpiozero logic when deploying to the Pi.
    """
    def __init__(self):
        self._inputs = {}
        self._outputs = {}

    def read_pin(self, pin):
        # Simulated read
        return self._inputs.get(pin, False)
        
    def write_pin(self, pin, value):
        # Simulated write
        self._outputs[pin] = value
        print(f"[GPIO AL] Pin {pin} set to {value}")

    def simulate_input(self, pin, value):
        self._inputs[pin] = value
        
gpio_manager = GPIOManager()

class ModbusManager:
    """
    Abstracts Modbus RTU calls via MAX485 on Hardware UART (GPIO14/15).
    Direction is controlled via GPIO21 (HIGH = Write, LOW = Read).
    """
    def __init__(self):
        self.direction_pin = 21
        self._sim_registers = {}

    def read_register(self, slave, address):
        gpio_manager.write_pin(self.direction_pin, False) # Read mode
        return self._sim_registers.get((slave, address), 0.0)

    def write_register(self, slave, address, value):
        gpio_manager.write_pin(self.direction_pin, True) # Write mode
        print(f"[MODBUS AL] Wrote {value} to Slave:{slave} Reg:{address}")
        self._sim_registers[(slave, address)] = value
        
modbus_manager = ModbusManager()

class WebSocketManager:
    """
    Abstracts external WebSocket Streams to continuously push or pull JSON data.
    """
    def __init__(self):
        self._cache = {}

    def read_stream(self, url, sensor_id):
        return self._cache.get((url, sensor_id), 0.0)

    def write_stream(self, url, sensor_id, data):
        print(f"[WEBSOCKET AL] Sending {data} to {url} for exact sensor '{sensor_id}'")
        self._cache[(url, sensor_id)] = data

ws_manager = WebSocketManager()



# --- Base Node Class ---
class BaseNode:
    def __init__(self, node_id, node_data):
        self.id = node_id
        self.data = node_data or {}
        # In PLCs, memory retention between scan cycles is crucial for timers/edge detectors
        self.state = {} 
        self.output_value = None

    def evaluate(self, inputs):
        """
        Inputs is a list of values provided by incoming edges.
        Must be implemented by subclasses.
        """
        raise NotImplementedError


# --- Input / Output Nodes ---
class DigitalInputNode(BaseNode):
    def evaluate(self, inputs):
        pin = self.data.get('pin')
        self.output_value = gpio_manager.read_pin(pin)

class DigitalOutputNode(BaseNode):
    def evaluate(self, inputs):
        pin = self.data.get('pin')
        # SCADA standard: default to False if no input
        val = any(inputs) if inputs else False 
        self.output_value = val
        gpio_manager.write_pin(pin, val)

class ModbusReadNode(BaseNode):
    def evaluate(self, inputs):
        slave = self.data.get('slave_id', 1)
        address = self.data.get('register_address', 0)
        self.output_value = modbus_manager.read_register(slave, address)

class ModbusWriteNode(BaseNode):
    def evaluate(self, inputs):
        slave = self.data.get('slave_id', 1)
        address = self.data.get('register_address', 0)
        # Writes the first valid input numeric value to the Modbus register
        val = inputs[0] if inputs and isinstance(inputs[0], (int, float)) else 0
        self.output_value = val
        modbus_manager.write_register(slave, address, val)

class WebsocketIngressNode(BaseNode):
    def evaluate(self, inputs):
        url = self.data.get('url', 'ws://localhost:5000/ws/stream/Engine_01')
        sensor_id = self.data.get('sensor_id', 'Engine_01')
        self.output_value = ws_manager.read_stream(url, sensor_id)

class WebsocketEgressNode(BaseNode):
    def evaluate(self, inputs):
        url = self.data.get('url', 'ws://localhost:5000/ws/sensor')
        sensor_id = self.data.get('sensor_id', 'Engine_01')
        val = inputs[0] if inputs else 0
        self.output_value = val
        ws_manager.write_stream(url, sensor_id, val)



# --- Logic Nodes ---
class AndNode(BaseNode):
    def evaluate(self, inputs):
        if not inputs:
            self.output_value = False
            return
        self.output_value = all(inputs)

class OrNode(BaseNode):
    def evaluate(self, inputs):
        self.output_value = any(inputs)

class ThresholdNode(BaseNode):
    OPERATORS = {
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        '==': operator.eq,
        '!=': operator.ne
    }
    def evaluate(self, inputs):
        val = inputs[0] if inputs else 0
        threshold = self.data.get('value', 0)
        op_str = self.data.get('operator', '==')
        op_func = self.OPERATORS.get(op_str, operator.eq)
        self.output_value = op_func(val, threshold)


# --- Timing & Signal Conditioning Nodes ---
class TimerOnNode(BaseNode):
    """TON: Output goes True only if input stays True continuously for 'delay' seconds."""
    def evaluate(self, inputs):
        active = any(inputs) if inputs else False
        delay = self.data.get('delay', 1.0)
        now = time.time()

        if active:
            if 'start_time' not in self.state:
                self.state['start_time'] = now
            elif now - self.state['start_time'] >= delay:
                self.output_value = True
                return
            self.output_value = False
        else:
            self.state.pop('start_time', None)
            self.output_value = False

class TimerOffNode(BaseNode):
    """TOF: Output goes False only if input stays False continuously for 'delay' seconds."""
    def evaluate(self, inputs):
        active = any(inputs) if inputs else False
        delay = self.data.get('delay', 1.0)
        now = time.time()

        if active:
            self.state.pop('off_start', None)
            self.output_value = True
        else:
            # If it was True, start timing the off delay
            if self.output_value:
                if 'off_start' not in self.state:
                    self.state['off_start'] = now
                elif now - self.state['off_start'] >= delay:
                    self.output_value = False
            else:
                self.output_value = False

class DebounceNode(BaseNode):
    """Prevents flickering by requiring stable input state for 'delay' seconds."""
    def evaluate(self, inputs):
        val = any(inputs) if inputs else False
        delay = self.data.get('delay', 0.5)
        now = time.time()

        last_val = self.state.get('last_val', val)
        stable_since = self.state.get('stable_since', now)

        if val != last_val:
            stable_since = now
            self.state['last_val'] = val
            self.state['stable_since'] = now

        if now - stable_since >= delay:
            self.output_value = val
        else:
            self.output_value = self.state.get('current_out', False)
            
        self.state['current_out'] = self.output_value


# --- Node Registry ---
NODE_REGISTRY = {
    'digital_input': DigitalInputNode,
    'digital_output': DigitalOutputNode,
    'and': AndNode,
    'or': OrNode,
    'threshold': ThresholdNode,
    'timer_on': TimerOnNode,
    'timer_off': TimerOffNode,
    'debounce': DebounceNode,
    'modbus_read': ModbusReadNode,
    'modbus_write': ModbusWriteNode,
    'websocket_ingress': WebsocketIngressNode,
    'websocket_egress': WebsocketEgressNode
}


# --- DAG Execution Engine ---
class PLCEngine:
    def __init__(self):
        self.nodes = {}       # id -> node instance
        self.edges = []       # [(source_id, target_id)]
        self.eval_order = []  # sorted node ids

    def load_graph(self, reactflow_json):
        """Builds identical Python instances from the visual React Flow JSON state"""
        self.nodes.clear()
        self.edges.clear()
        self.eval_order.clear()

        # Instantiate Nodes natively using standard dict passing
        for n in reactflow_json.get('nodes', []):
            node_type = n.get('type')
            if node_type in NODE_REGISTRY:
                self.nodes[n['id']] = NODE_REGISTRY[node_type](n['id'], n.get('data'))
            else:
                print(f"[Warning] Unknown node type '{node_type}' ignored.")

        # Map edges mapping
        for e in reactflow_json.get('edges', []):
            src = e.get('source')
            tgt = e.get('target')
            if src in self.nodes and tgt in self.nodes:
                self.edges.append((src, tgt))

        self._topological_sort()

    def _topological_sort(self):
        """Computes deterministic DAG execution order (evaluates dependencies first)."""
        in_degree = {nid: 0 for nid in self.nodes}
        adj = defaultdict(list)

        for src, tgt in self.edges:
            adj[src].append(tgt)
            in_degree[tgt] += 1

        # Start with nodes having 0 dependencies
        queue = deque([nid for nid in self.nodes if in_degree[nid] == 0])
        sorted_nodes = []

        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(node_id)
            for neighbor in adj[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_nodes) != len(self.nodes):
            print("[Warning] Cyclic dependency detected! Engine execution may be unpredictable.")
            # Simple fallback for cyclic logic: just evaluate sorted ones then the remainder arbitrarily
            remainder = set(self.nodes.keys()) - set(sorted_nodes)
            sorted_nodes.extend(list(remainder))

        self.eval_order = sorted_nodes

    def scan_cycle(self):
        """
        Executes exactly one continuous synchronous scan of the PLC logic layer.
        Typical PLCs run this as fast as possible in a while True loop.
        """
        for node_id in self.eval_order:
            node = self.nodes[node_id]

            # Gather inputs exactly as they stand sequentially
            incoming_values = []
            for src, tgt in self.edges:
                if tgt == node_id:
                    source_out = self.nodes[src].output_value
                    incoming_values.append(source_out)

            # Execution is safely isolated & bounded to each subclass definition. 
            # Absolutely no dynamic `eval` parsing occurs.
            node.evaluate(incoming_values)

        return {n_id: self.nodes[n_id].output_value for n_id in self.eval_order}


if __name__ == "__main__":
    # Internal Unit Test demonstrating capabilities
    engine = PLCEngine()
    
    mock_reactflow = {
        "nodes": [
            {"id": "in1", "type": "digital_input", "data": {"pin": 4}},
            {"id": "deb1", "type": "debounce", "data": {"delay": 0.5}},
            {"id": "ton1", "type": "timer_on", "data": {"delay": 1.0}},
            {"id": "out1", "type": "digital_output", "data": {"pin": 17}}
        ],
        "edges": [
            {"source": "in1", "target": "deb1"},
            {"source": "deb1", "target": "ton1"},
            {"source": "ton1", "target": "out1"}
        ]
    }
    
    engine.load_graph(mock_reactflow)
    print("Topological Sort Order:", engine.eval_order)

    print("\n--- Starting Scan Simulation ---")
    gpio_manager.simulate_input(4, True) # Simulating setting Pin 4 HIGH
    
    for i in range(20): # Simulating 2 seconds (10 scans/sec)
        out = engine.scan_cycle()
        print(f"Scan {i}: Final Motor Output State -> {out.get('out1')}")
        time.sleep(0.1)
