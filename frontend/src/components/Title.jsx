import React from 'react'

function Title({ style, styleBlock }) {
    return (
        <div style={{display: "flex", alignItems: "center", ...styleBlock}}>
            <span style={{...style, color: "#F4F5f5"}}>Goph</span>
            <span style={{...style, color: "#008645"}}>Keeper</span>
        </div>
    )
}

export default Title;