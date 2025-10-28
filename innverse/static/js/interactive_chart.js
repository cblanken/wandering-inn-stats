addEventListener("DOMContentLoaded", (e) => {
  const iframe = document.querySelector(`.interactive-chart`);

  iframe.onload = (frame_event) => {
    const iframeStyles = iframe.contentDocument.createElement(`style`);
    iframeStyles.innerHTML = `
      html {
        height: 100%;
        overflow: hidden;
      }
    `;

    iframe.contentDocument.head.appendChild(iframeStyles);
  }
});
