// Clicking the toolbar icon opens the uploader page (the queue lives there, files stay in that tab).
chrome.action.onClicked.addListener(() => {
  chrome.tabs.create({ url: chrome.runtime.getURL('uploader.html') });
});
