function Header(el)
  if el.level ~= 1 then
    return nil
  end

  local text = pandoc.utils.stringify(el.content)
  local number, title = text:match("^%s*(%d+)%.%s+(.+)%s*$")
  if number then
    local title_tex = pandoc.write(
      pandoc.Pandoc({pandoc.Para(pandoc.read(title, "markdown").blocks[1].content)}),
      "latex"
    ):gsub("%s+$", "")
    return pandoc.RawBlock(
      "latex",
      "\\bookchapter{" .. number .. "}{" .. title_tex .. "}"
    )
  end

  local epilog_title = text:match("^%s*Epilog%.%s+(.+)%s*$")
  if epilog_title then
    local title_tex = pandoc.write(
      pandoc.Pandoc({pandoc.Para(pandoc.read(epilog_title, "markdown").blocks[1].content)}),
      "latex"
    ):gsub("%s+$", "")
    return pandoc.RawBlock("latex", "\\bookepilog{" .. title_tex .. "}")
  end

  return nil
end
