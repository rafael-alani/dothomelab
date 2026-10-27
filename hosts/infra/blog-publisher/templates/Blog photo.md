<%*
const photos = app.vault.getFiles().filter(file => /\.(jpe?g|png|webp|avif|gif|svg)$/i.test(file.path));
const photo = await tp.system.suggester(file => file.path, photos, false, "Choose a photo");
if (photo) {
  const description = await tp.system.prompt("Description (optional, shown after opening the photo)", "", false, true);
  tR += "\n---\n[[" + photo.path + "]]\n" + (description?.trim() ? description.trim() + "\n" : "") + "---\n";
}
%>
