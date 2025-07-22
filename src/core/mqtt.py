"""
MQTT Client for sensor data publishing and command subscription.
"""
import json
import logging
from typing import Any, Callable, Dict, Optional

import paho.mqtt.client as mqtt

from .constants import DEFAULT_MQTT_PORT, DEFAULT_MQTT_QOS

logger = logging.getLogger(__name__)

class MqttClient:
    """MQTT client wrapper."""
    
    def __init__(
        self,
        client_id: str,
        host: str = "localhost",
        port: int = DEFAULT_MQTT_PORT,
        username: Optional[str] = None,
        password: Optional[str] = None,
        keepalive: int = 60
    ):
        """Initialize MQTT client.
        
        Args:
            client_id: Client identifier
            host: MQTT broker host
            port: MQTT broker port
            username: MQTT username
            password: MQTT password
            keepalive: Keepalive timeout in seconds
        """
        self.client = mqtt.Client(
            client_id=client_id,
            protocol=mqtt.MQTTv5
        )
        
        if username:
            self.client.username_pw_set(username, password)
            
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self._handlers = {}
        
    def connect(self) -> None:
        """Connect to MQTT broker."""
        try:
            self.client.connect(
                self.host,
                self.port,
                self.keepalive
            )
            self.client.loop_start()
            logger.info(
                f"Connected to MQTT broker at {self.host}:{self.port}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
            
    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
        except Exception as e:
            logger.error(f"Error disconnecting from MQTT broker: {e}")
            
    def publish(
        self,
        topic: str,
        payload: Any,
        qos: int = DEFAULT_MQTT_QOS
    ) -> None:
        """Publish message to topic.
        
        Args:
            topic: Topic to publish to
            payload: Message payload
            qos: Quality of service level
        """
        try:
            self.client.publish(topic, payload, qos)
            logger.debug(f"Published to {topic}")
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            
    def subscribe(
        self,
        topic: str,
        handler: Callable,
        qos: int = DEFAULT_MQTT_QOS
    ) -> None:
        """Subscribe to topic.
        
        Args:
            topic: Topic to subscribe to
            handler: Callback function for messages
            qos: Quality of service level
        """
        try:
            self.client.subscribe(topic, qos)
            self._handlers[topic] = handler
            logger.info(f"Subscribed to {topic}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")
            
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Handle connection established.
        
        Args:
            client: MQTT client instance
            userdata: User data
            flags: Connection flags
            rc: Return code
            properties: Protocol v5 properties
        """
        if rc == 0:
            logger.info("MQTT connection established")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            
    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Handle disconnection.
        
        Args:
            client: MQTT client instance
            userdata: User data
            rc: Return code
            properties: Protocol v5 properties
        """
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection")
            
    def _on_message(self, client, userdata, message):
        """Handle received message.
        
        Args:
            client: MQTT client instance
            userdata: User data
            message: Received message
        """
        try:
            handler = self._handlers.get(message.topic)
            if handler:
                handler(message.topic, message.payload)
            else:
                logger.warning(f"No handler for topic {message.topic}")
        except Exception as e:
            logger.error(f"Error handling message: {e}") 