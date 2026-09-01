# Multi-Tofu

Gestor multicuenta de Dofus para macOS. Cambio instantáneo entre clientes, rueda
de personajes y equipos, para Dofus 3 (Unity).

**[Web](https://minutesback.github.io/multi-tofu/es/)** · **[English](README.md)** · **[Français](README.fr.md)** · **Español** · **[Português](README.pt.md)**

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
- **Rueda o panel de grupo.** Mantén tu tecla y elige el cliente a poner
  delante. Dos estilos, a elegir en los ajustes: una rueda bajo el cursor, o un
  panel de grupo a la izquierda parecido al marco de grupo de Dofus, una corona
  en tu líder y la tecla de acceso en cada personaje.
- **Equipos.** Reparte tus personajes y rota solo dentro del equipo activo.
- **Teclas directas.** Una tecla fija por personaje.
- **Mac + VM de Windows.** Ejecuta un cliente de Dofus directamente en el Mac y
  otro en VMware Fusion. La VM se une a la misma rotación, rueda y teclas
  directas. Multi-Tofu se queda en el Mac, sin instalar nada en Windows.
- **Barra de menús.** Haz clic en un personaje para traerlo al frente, cambia de
  rotación, abre los ajustes.
- **Cuatro idiomas.** Inglés, francés, español y portugués, según tu sistema en
  el primer arranque y cambiables en cualquier momento.
- **Roles.** Marca cada personaje y la rueda colorea su porción según el rol.
  Pasados cinco clientes, un color se lee más rápido que seis nombres.
- **Vistazo.** Mantén una tecla para mirar otro cliente, suéltala y vuelves
  donde estabas, con tu posición en la rotación intacta.
- **Orden por número.** Escribe una posición para colocar un personaje, útil
  cuando el orden sigue la iniciativa y no el orden en que abriste los clientes.
- **No molesta.** Abre los ajustes la primera vez para configurarlo y luego se
  queda callado en la barra de menús. Una vez en marcha no vuelve a primer
  plano, ni cuando el Launcher de Ankama lo reabre.
- **Una tecla, una acción.** Asignar una tecla que ya tiene otro atajo se la
  quita a ese, en vez de dejar una acción que nunca se activa.
- **Solo el cliente en el que estás.** Activa el ocultado y los demás clientes
  desaparecen mientras juegas el de delante. Siguen corriendo y vuelven en
  cuanto cambias a ellos.

## Dónde se guardan tus ajustes

Todo lo que configuras se escribe en
`~/Library/Application Support/Multi-Tofu/config.json` en cuanto lo cambias,
indexado por nombre de personaje. Orden de rotación, equipos, roles, líder,
teclas directas y todos los atajos. Cierra los clientes, cierra la app, vuelve
una semana después, conecta los mismos personajes y está tal cual lo dejaste.

Los iconos de clase se leen del juego, no se adivinan. El título de la ventana
lleva la clase, así que un Eniripsa muestra el icono de Eniripsa sin que le
digas nada. La última clase conocida se recuerda por personaje, así que un
cliente que aún está cargando ya muestra la correcta.

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
[Releases](https://github.com/MinutesBack/multi-tofu/releases), descomprímelo y
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
| Vistazo a otro cliente | mantener ` |
| Abrir ajustes | Control + F1 |

Todo se puede cambiar en los ajustes. Los atajos se guardan como códigos de
tecla física, así que sobreviven a un cambio entre AZERTY y QWERTY.

## Desde el código

```
git clone https://github.com/MinutesBack/multi-tofu.git
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
