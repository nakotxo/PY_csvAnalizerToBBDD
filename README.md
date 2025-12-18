# PY_csvAnalizerToBBDD

Analizador de CSV para integrar datos en Base de Datos - Lenguaje Python

## Descripción

Aplicación web Flask que procesa archivos CSV con datos de usuarios, valida la información (DNI/NIE/CIF, emails, teléfonos) y inserta los registros válidos en la tabla `wp_users` de WordPress.

## Características

- ✅ Validación de identificadores españoles (DNI, NIE, CIF)
- ✅ Normalización y validación de emails
- ✅ Limpieza y priorización de números de teléfono
- ✅ Inserción automática en tabla WordPress `wp_users`
- ✅ Generación de archivos CSV con resultados
- ✅ Interfaz web moderna con Bootstrap

## Instalación

1. **Instalar dependencias:**

   ```bash
   pip install -r dependencias.txt
   ```

2. **Configurar variables de entorno:**
   Crear un archivo `.env` con:

   ```
   SESSION_SECRET=tu_clave_secreta_aqui
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=tu_usuario
   DB_PASSWORD=tu_password
   DB_NAME=tu_base_de_datos
   ```

3. **Ejecutar la aplicación:**
   ```bash
   python app.py
   ```
   O usando el script:
   ```bash
   start.bat
   ```

## Uso

1. Accede a `http://localhost:5000`
2. Sube un archivo CSV con columnas: `dni`, `telefono`, `email` (y otras opcionales)
3. La aplicación validará los datos e insertará los válidos en la tabla `wp_users`
4. Descarga los archivos CSV con resultados

## Estructura de la Base de Datos

La aplicación inserta usuarios válidos en la tabla `wp_users` de WordPress existente:

- `ID`: ID único del usuario (auto-incremental)
- `user_login`: Nombre de usuario (usa el DNI como login único)
- `user_email`: Email del usuario (normalizado)
- `user_registered`: Fecha de registro
- `display_name`: Nombre para mostrar
- `user_status`: Estado del usuario (0 = activo)

**Nota**: Se usa una contraseña por defecto que debe cambiarse posteriormente por seguridad.

## Validaciones

- **DNI/NIE/CIF**: Verificación de formato y dígito de control
- **Email**: Validación de formato y normalización
- **Teléfono**: Limpieza y priorización de móviles sobre fijos
