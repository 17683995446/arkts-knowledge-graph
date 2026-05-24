/**
 * 嵌套组件文件 - 深度 15
 */

import { NestedComponent16 } from './NestedComponentFile16';

@Component
export struct NestedComponent15 {

    build() {
        Column() {
            NestedComponent16()
            NestedComponent16()
            NestedComponent16()
        }
    }

}
