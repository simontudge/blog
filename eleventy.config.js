module.exports = function (eleventyConfig) {
  // Only Markdown and Nunjucks are treated as templates. Every existing .html
  // file is copied through untouched, so URLs that are already live keep
  // working and posts can be converted to Markdown one at a time.
  eleventyConfig.setTemplateFormats(["md", "njk"]);

  const IMAGES = "{jpg,JPG,jpeg,JPEG,png,PNG,webp,gif}";
  // style.css is only used by the unpublished film pages; it stays in the
  // repo for them but is no longer copied into the site.
  eleventyConfig.addPassthroughCopy("site.css");
  for (const section of ["short-stories", "travel-blog"]) {
    eleventyConfig.addPassthroughCopy(`${section}/**/*.html`);
    eleventyConfig.addPassthroughCopy(`${section}/**/*.${IMAGES}`);
  }

  // Scratch templates from the hand-written days, not part of the site.
  eleventyConfig.ignores.add("templates/**");
  // The film reviews stay in the repo but are no longer published.
  eleventyConfig.ignores.add("film/**");
  // Working notes, not posts.
  eleventyConfig.ignores.add("todo.md");
  eleventyConfig.ignores.add("**/README.md");

  return {
    dir: {
      input: ".",
      output: "_site",
      includes: "_includes",
    },
    markdownTemplateEngine: "njk",
  };
};
