# Sistema IoT de Vigilancia basado en Edge Computing

## Descripción General

Este proyecto presenta el diseño, implementación y evaluación de un sistema inteligente de vigilancia y alerta remota orientado a mitigar problemas de inseguridad ciudadana mediante tecnologías de Internet de las Cosas (IoT) y Edge Computing. 

A diferencia de las cámaras comerciales convencionales que operan como cajas cerradas y saturan el canal de subida (uplink) al transmitir flujos de video continuo hacia servidores en la nube, esta arquitectura de código abierto procesa las activaciones de movimiento de forma local. Utilizando sensores infrarrojos pasivos (PIR), el sistema captura y transmite información fotográfica en ráfagas únicamente ante eventos confirmados. Esto garantiza un uso altamente eficiente del ancho de banda y evita la congestión en las redes residenciales asimétricas.

## Arquitectura del Sistema

El diseño se fundamenta en una topología plana de red local y el desacoplamiento de servicios a través de los siguientes componentes:

* **Nodos Perceptores (Edge Nodes):** Integrados por placas de desarrollo de bajo costo (Raspberry Pi Zero 2W y ESP32-CAM) que asumen la carga de captura multimedia directamente en el borde de la red.
* **Servidor Middleware:** Un servidor local desarrollado en Flask que actúa como puente de gestión, administrando la comunicación interna de la red LAN de forma stateless y manteniendo los nodos aislados de la red pública.
* **Alertas Asíncronas:** Comunicación externa cifrada hacia la API de Telegram mediante el protocolo TLS 1.3, permitiendo notificaciones remotas en tiempo real de forma segura.

## Metodología y Rendimiento

La viabilidad de esta topología fue validada en un entorno físico de red inalámbrica bajo el estándar IEEE 802.11n en la banda de 2.4 GHz. Mediante herramientas de auditoría de tráfico e Inspección Profunda de Paquetes (DPI) como Wireshark, se evaluaron métricas críticas de latencia y throughput. 

Los resultados experimentales demostraron una gestión óptima del espectro utilizando el mecanismo de control de acceso CSMA/CA, logrando transmisiones íntegras con cero retransmisiones TCP. Esto certifica que la red es capaz de entregar alertas multimedia sin experimentar pérdida de paquetes por congestión o colisiones en el medio compartido.

## Organización del Repositorio

Todo el contenido técnico del proyecto se encuentra organizado y distribuido en las distintas carpetas de este repositorio. Cada directorio alberga los archivos fuente, configuraciones y documentación correspondiente a los nodos de hardware específicos (microcontroladores y microprocesadores) y al despliegue del servidor intermediario local, permitiendo una fácil navegación y replicación de la arquitectura.

## Autores

* **Carlos Nicolas Morales Cuellar**
* **Jose Ramos Ramos Calzada**
* **Ronald Enrique Rojas Crisostomo**

**Institución:** Universidad Nacional Mayor de San Marcos (UNMSM) - Lima, Perú.
