/**
 * 循环导入链 1, 文件 2
 */

import { Class0 } from './CircularChain1_0';

export class Class2 {
    use0() {
        return new Class0();
    }
}
