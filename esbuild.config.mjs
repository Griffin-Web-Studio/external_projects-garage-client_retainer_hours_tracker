import * as esbuild from "esbuild";

const watch = process.argv.includes("--watch");

const ctx = await esbuild.context({
  entryPoints: ["static/src/index.ts"],
  bundle: true,
  outfile: "static/build/js/index.js",
  target: "es6",
  minify: true,
  sourcemap: true,
});

if (watch) {
  await ctx.watch();
  console.log("Watching for changes...");
} else {
  await ctx.rebuild();
  await ctx.dispose();
}
