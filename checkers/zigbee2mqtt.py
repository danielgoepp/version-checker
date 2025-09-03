import json
import time
import paho.mqtt.client as paho
import config

def get_zigbee2mqtt_version(instance):
    """Get Zigbee2MQTT version via MQTT for a specific instance"""
    try:
        current_version = None
        
        def on_message(client, userdata, message):
            nonlocal current_version
            try:
                data = json.loads(message.payload.decode())
                current_version = data.get("version")
                print(f"  {instance}: {current_version}")
            except Exception as e:
                print(f"  {instance}: Error parsing MQTT message - {e}")
        
        client = paho.Client(paho.CallbackAPIVersion.VERSION2, f"version_manager_{instance}")
        client.username_pw_set(username=config.MQTT_USERNAME, password=config.MQTT_PASSWORD)
        client.on_message = on_message
        
        client.connect(config.MQTT_BROKER)
        client.loop_start()
        client.subscribe([(f"{instance}/bridge/info", 0)])
        time.sleep(2)  # Wait for message
        client.disconnect()
        client.loop_stop()
        
        return current_version
    except Exception as e:
        print(f"  {instance}: Error getting version - {e}")
        return None