module.exports = {
  apps: [
    {
      name: "fileship-srv",
      script: "uwsgi",
      args: "--ini uwsgi.ini",
      interpreter: "none", // Use the default system interpreter
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
    },
  ],
};
