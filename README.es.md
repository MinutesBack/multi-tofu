# Multi-Tofu

Gestor multicuenta de Dofus para macOS. Cambio instantáneo entre clientes, rueda
de personajes y equipos, para Dofus 3 (Unity).

**[English](README.md)** · **[Français](README.fr.md)** · **Español** · **[Português](README.pt.md)**

Port independiente para macOS de [Dosoft](https://www.dosoft.fr), que solo
existe en Windows. Nada del código Windows sirve, está construido sobre la API
Win32, así que todo está reescrito sobre la API de Accesibilidad de macOS, un
CGEventTap y AppKit.

<p align="center">
  <img src="docs/wheel.png" alt="La rueda de personajes" width="380">
</p>

![Ajustes](docs/preferences.png)

## Qué hace

- **Cambio instantáneo.** Atajos globales pasan al cliente siguiente o anterior,
  o vuelven directamente a tu líder.
- **Rueda de personajes.** Mantén Opción, aparece una rueda bajo el cursor con
  el icono de clase de cada personaje. Mueve el ratón, suelta, ese cliente pasa
  al frente.
- **Equipos.** Reparte tus personajes y rota solo dentro del equipo activo.
- **Teclas directas.** Una tecla fija por personaje.
- **Barra de menús.** Haz clic en un personaje para traerlo al frente, cambia de
  rotación, abre los ajustes.
- **Cuatro idiomas.** Inglés, francés, español y portugués, según tu sistema en
  el primer arranque y cambiables en cualquier momento.

## Los nombres de los personajes

No los escribes tú. Multi-Tofu lee el título de la ventana de Dofus, así que en
cuanto un personaje inicia sesión su nombre real aparece en la rueda, en el menú
y en los ajustes.

Un cliente abierto pero todavía en la pantalla de conexión no tiene personaje,
así que se muestra como `Cuenta 1`, `Cuenta 2` y así. Esas entradas siguen
visibles en el menú, donde puedes hacer clic para ir a conectarte, pero quedan
fuera de la rotación de F1 para que una pulsación nunca te lleve a una ventana
sin personaje. Pon `login_windows_in_rotation` en true si las quieres incluir.

## Instalación

Descarga el `.zip` desde la página de
[Releases](https://github.com/JMax92/multi-tofu/releases), descomprímelo y
arrastra `Multi-Tofu.app` a Aplicaciones.

La app no está firmada con una cuenta de desarrollador de Apple, así que la
primera vez haz clic derecho sobre el icono y elige **Abrir**, luego confirma.
Si macOS sigue negándose, ve a Ajustes del Sistema > Privacidad y seguridad y
pulsa **Abrir de todos modos**.

Es universal, funciona en Apple Silicon y en Intel.

## Permiso de Accesibilidad

En el primer arranque macOS pide Accesibilidad. Multi-Tofu la necesita para leer
los títulos de las ventanas de Dofus y para escuchar tus atajos.

Ajustes del Sistema > Privacidad y seguridad > Accesibilidad, y activa
Multi-Tofu. No hace falta salir, los atajos se activan solos en unos segundos.

Sin icono en el Dock por defecto, la app vive en la barra de menús. Si tu barra
está llena, macOS esconde el icono detrás de la muesca, la app lo detecta y te
ofrece un icono en el Dock.

## Atajos por defecto

| Acción | Tecla |
| --- | --- |
| Personaje siguiente | F1 |
| Personaje anterior | F2 |
| Ir al líder | F3 |
| Buscar ventanas | F4 |
| Rueda de personajes | mantener Opción |
| Abrir ajustes | Control + F1 |

Todo se puede cambiar en los ajustes. Los atajos se guardan como códigos de
tecla física, así que sobreviven a un cambio entre AZERTY y QWERTY.

## Desde el código

```
git clone https://github.com/JMax92/multi-tofu.git
cd multi-tofu
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./run.sh
```

Ejecútalo desde Terminal.app y autoriza Terminal en Accesibilidad, o compila la
app con `./tools/build_app.sh --install` y autoriza Multi-Tofu.

`./run.sh --probe` muestra lo que la app detecta.

## Configuración

`~/Library/Application Support/Multi-Tofu/config.json`

- `language`: auto, en, fr, es o pt.
- `login_windows_in_rotation`: incluir o no las ventanas de conexión.
- `wheel_delay_ms`: cuánto hay que mantener Opción antes de que salga la rueda.
- `swallow_bound_keys`: impedir que las teclas asignadas lleguen a Dofus.
- `show_dock_icon`: mostrar un icono en el Dock.

## Limitaciones conocidas

- **Pantalla completa.** La rueda es una capa superpuesta. Sobre un cliente en
  pantalla completa exclusiva puede no dibujarse. Juega en ventana o sin bordes.
- **El Autofocus de Retro no está portado.** Lee las notificaciones toast de
  Windows y macOS no tiene equivalente para una app de terceros.
- **Dofus Retro todavía no está soportado.** Solo Unity.

## Licencia

Apache 2.0, ver [LICENSE](LICENSE) y [NOTICE](NOTICE).

Multi-Tofu no está afiliado a Ankama Games, ni respaldado ni patrocinado por
ellos. DOFUS y todos los nombres e imágenes asociados son propiedad de Ankama
Games.
