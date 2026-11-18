/**
 * Remove numeric citation markers from the text sent to TTS, without changing
 * the raw assistant text or the source payload sent to the browser.
 */
export async function* filterCitationMarkers(source: AsyncIterable<string>): AsyncIterable<string> {
  let pending = "";
  let hasEmittedText = false;

  for await (const chunk of source) {
    const combined = pending + chunk;
    const partialMarker = combined.match(/\[\d*$/);
    const safeEnd = partialMarker?.index ?? combined.length;
    let safeText = combined.slice(0, safeEnd);
    pending = combined.slice(safeEnd);

    const trailingWhitespace = safeText.match(/\s+$/)?.[0] ?? "";
    if (trailingWhitespace) {
      safeText = safeText.slice(0, -trailingWhitespace.length);
      pending = trailingWhitespace + pending;
    }

    const filtered = safeText.replace(/\s*\[\d+\]/g, "").replace(/\s{2,}/g, " ");
    const output = hasEmittedText ? filtered : filtered.trimStart();
    if (output) {
      yield output;
      if (/\S/.test(output)) hasEmittedText = true;
    }
  }
}
