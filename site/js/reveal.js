// reveal.js: page sections that start below the fold fade and rise into place the
// first time they scroll into view (styles: .reveal / .reveal--in in styles.css).
// Sections already on screen at load are left alone, and with reduced motion
// (or without JavaScript) everything simply shows.

if (!matchMedia("(prefers-reduced-motion: reduce)").matches && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("reveal--in");
      observer.unobserve(entry.target);             // once only
    }
  }, { rootMargin: "0px 0px -60px 0px" });          // start once 60px of it is on screen

  for (const el of document.querySelectorAll(".page > *")) {
    if (el.getBoundingClientRect().top < innerHeight) continue;
    el.classList.add("reveal");
    observer.observe(el);
  }
}
