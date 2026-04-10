-- side_by_side_figures.lua
--
-- Combines multiple Figure blocks into a single LaTeX float with N minipages
-- laid out side by side. Each subfigure keeps its own \caption (so it gets
-- its own auto-incremented "Figure N" number) and \label (so existing
-- pandoc-crossref references like @fig:foo continue to resolve via LaTeX
-- \ref).
--
-- Two trigger modes:
--   1. Strict adjacency: a run of two or more Figure blocks with no
--      intervening blocks of any other kind is combined automatically.
--   2. Explicit marker: a Div with class `sidebyside` (e.g.
--      `::: sidebyside ... :::`) — all Figure blocks inside the div are
--      combined into one side-by-side float, emitted at the position of
--      the first figure. Non-Figure content in the div is preserved in
--      its original position. Use this when figures need to be paired
--      across paragraph breaks or other intervening content.
--
-- The whole combined float is emitted as a single RawBlock. If we instead
-- interleaved RawBlocks with normal AST blocks, pandoc's LaTeX writer would
-- insert blank lines around each RawBlock, which become \par's at compile
-- time and break the side-by-side flow (the second minipage drops onto a
-- new line). One big RawBlock keeps the layout tight.
--
-- Because we emit the image-include line ourselves, we have to mirror what
-- pandoc would do: \includesvg for .svg files, \includegraphics for raster
-- formats. Both are wrapped in \pandocbounded (defined in preamble.tex) so
-- they obey the same scaling rules as standalone figures.
--
-- Wired into defaults.yaml after pandoc-crossref so cross-references are
-- already in their final \ref{} form by the time we restructure the figure.

local function inlines_to_latex(inlines)
  if not inlines or #inlines == 0 then return "" end
  local doc = pandoc.Pandoc({ pandoc.Plain(inlines) })
  local s = pandoc.write(doc, "latex")
  return (s:gsub("%s+$", ""))
end

local function get_caption_inlines(fig)
  local cap = fig.caption
  if not cap then return {} end
  if cap.long and #cap.long > 0 then
    return pandoc.utils.blocks_to_inlines(cap.long)
  end
  return {}
end

local function get_first_image(fig)
  local img
  pandoc.walk_block(fig, {
    Image = function(el)
      if not img then img = el end
    end,
  })
  return img
end

-- Resolve a relative image src to an absolute path by walking
-- PANDOC_STATE.resource_path. Pandoc normally does this implicitly when it
-- emits an Image, but since we're producing raw LaTeX it's our job: xelatex
-- runs in a temp dir, so a bare `figures/foo.png` would not be found unless
-- we bake an absolute path into the \includegraphics call.
local function resolve_image_src(src)
  if src:match("^/") or src:match("^[a-zA-Z]+://") then
    return src
  end
  local cwd = pandoc.system.get_working_directory()
  local rps = (PANDOC_STATE and PANDOC_STATE.resource_path) or { "." }
  for _, dir in ipairs(rps) do
    local base = dir
    if not base:match("^/") then
      base = cwd .. "/" .. base
    end
    local candidate = base .. "/" .. src
    local f = io.open(candidate, "rb")
    if f then
      f:close()
      return candidate
    end
  end
  return src
end

-- Mirror pandoc's image-include logic: \includesvg for SVG, \includegraphics
-- for everything else. The result is wrapped in \pandocbounded so the same
-- size/aspect rules apply as for normal pandoc figures.
local function image_include(src)
  local resolved = resolve_image_src(src)
  local lower = resolved:lower()
  local cmd
  if lower:sub(-4) == ".svg" or lower:sub(-5) == ".svgz" then
    cmd = string.format("\\includesvg[keepaspectratio]{%s}", resolved)
  else
    cmd = string.format("\\includegraphics[keepaspectratio]{%s}", resolved)
  end
  return "\\pandocbounded{" .. cmd .. "}"
end

-- Build a side-by-side LaTeX float from a list of N >= 2 Figure blocks and
-- return it as a single RawBlock.
local function combine_figures(figs)
  local n = #figs
  -- Equal-width minipages, leaving a small gap so \hfill has room.
  local width = string.format("%.4f", 0.98 / n)

  local parts = { "\\begin{figure}[htbp]%\n\\centering%" }

  for i, fig in ipairs(figs) do
    local img = get_first_image(fig)
    if not img then return nil end

    local caption_latex = inlines_to_latex(get_caption_inlines(fig))
    local label = fig.identifier or ""
    local label_cmd = ""
    if label ~= "" then
      label_cmd = "\\label{" .. label .. "}"
    end

    -- Each line ends with `%` to suppress the trailing newline that LaTeX
    -- would otherwise turn into a space (or, after a blank line, a \par).
    parts[#parts + 1] = string.format("\\begin{minipage}[t]{%s\\textwidth}%%", width)
    parts[#parts + 1] = "\\centering%"
    parts[#parts + 1] = image_include(img.src) .. "%"
    parts[#parts + 1] = string.format("\\caption{%s}%s%%", caption_latex, label_cmd)
    if i < n then
      parts[#parts + 1] = "\\end{minipage}\\hfill%"
    else
      parts[#parts + 1] = "\\end{minipage}%"
    end
  end

  parts[#parts + 1] = "\\end{figure}"

  return pandoc.RawBlock("latex", table.concat(parts, "\n"))
end

function Blocks(blocks)
  local result = pandoc.List()
  local i = 1
  while i <= #blocks do
    local b = blocks[i]
    if b.t == "Figure" and blocks[i + 1] and blocks[i + 1].t == "Figure" then
      local run = { b, blocks[i + 1] }
      local j = i + 2
      while blocks[j] and blocks[j].t == "Figure" do
        run[#run + 1] = blocks[j]
        j = j + 1
      end
      local combined = combine_figures(run)
      if combined then
        result:insert(combined)
      else
        for _, x in ipairs(run) do result:insert(x) end
      end
      i = j
    else
      result:insert(b)
      i = i + 1
    end
  end
  return result
end

-- Explicit marker: ::: sidebyside ... :::
-- All Figure blocks inside the div are combined into one float at the
-- position of the first figure. Other blocks inside the div are kept where
-- they were.
function Div(div)
  if not div.classes:includes("sidebyside") then return nil end
  local figs = {}
  for _, b in ipairs(div.content) do
    if b.t == "Figure" then figs[#figs + 1] = b end
  end
  if #figs < 2 then return nil end
  local combined = combine_figures(figs)
  if not combined then return nil end
  local out = pandoc.List()
  local emitted = false
  for _, b in ipairs(div.content) do
    if b.t == "Figure" then
      if not emitted then
        out:insert(combined)
        emitted = true
      end
      -- skip subsequent figures (already absorbed)
    else
      out:insert(b)
    end
  end
  return out
end
