VENV="/workspace/venv"
if [ -n "$PS1" ] && [ -f "$VENV/bin/activate" ]; then
  . "$VENV/bin/activate"
fi